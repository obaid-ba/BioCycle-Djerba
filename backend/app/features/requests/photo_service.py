"""Photo business logic for collection requests.

Validates and stores uploaded photos (MIME allow-list, per-file size cap, per-
request quota), enforces ownership + lifecycle rules, and serves photos only
after an access check. Coordinates disk writes (``photo_storage``) with
``RequestPhoto`` rows and owns the transaction boundary.
"""

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.features.auth.models import User
from app.features.requests import photo_storage
from app.features.requests.models import CollectionRequest, RequestPhoto
from app.features.requests.service import RequestService
from app.features.requests.state_machine import TERMINAL_STATES
from app.shared.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

# Read files from the multipart stream in modest chunks so a large upload never
# balloons memory; the size cap is enforced as we go.
_CHUNK_SIZE = 64 * 1024


class PhotoService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.requests = RequestService(db)

    async def _get_request_owned(self, request_id: uuid.UUID, user: User) -> CollectionRequest:
        # Reuses the request service's RBAC scoping (404 for others' requests).
        return await self.requests.get_or_404(request_id, user)

    async def _get_photo(
        self, request_id: uuid.UUID, photo_id: uuid.UUID
    ) -> RequestPhoto:
        photo = await self.db.get(RequestPhoto, photo_id)
        # The photo must belong to the request named in the URL, else 404.
        if photo is None or photo.request_id != request_id:
            raise NotFoundError("Photo not found")
        return photo

    async def _current_count(self, request_id: uuid.UUID) -> int:
        stmt = select(RequestPhoto).where(RequestPhoto.request_id == request_id)
        result = await self.db.execute(stmt)
        return len(result.scalars().all())

    # ------------------------------------------------------------------ upload
    async def upload(
        self, request_id: uuid.UUID, files: list[UploadFile], user: User
    ) -> list[RequestPhoto]:
        req = await self._get_request_owned(request_id, user)

        # Frozen once the request is closed out — photos are evidence.
        if req.status in TERMINAL_STATES:
            raise ConflictError(
                f"Cannot modify photos of a {req.status.value} request"
            )

        if not files:
            raise ValidationError("No files provided")

        existing = await self._current_count(request_id)
        if existing + len(files) > settings.MAX_PHOTOS_PER_REQUEST:
            raise ConflictError(
                f"A request may have at most {settings.MAX_PHOTOS_PER_REQUEST} photos "
                f"({existing} already uploaded)"
            )

        created: list[RequestPhoto] = []
        written_paths: list[str] = []
        try:
            for upload in files:
                photo = await self._store_one(request_id, upload)
                written_paths.append(photo.storage_path)
                created.append(photo)
            await self.db.commit()
        except BaseException:
            # Roll back DB and remove any files written this call — no orphans.
            await self.db.rollback()
            for path in written_paths:
                photo_storage.delete_file(path)
            raise

        for photo in created:
            await self.db.refresh(photo)
        return created

    async def _store_one(
        self, request_id: uuid.UUID, upload: UploadFile
    ) -> RequestPhoto:
        content_type = (upload.content_type or "").lower()
        if content_type not in settings.ALLOWED_PHOTO_TYPES:
            raise ValidationError(
                f"Unsupported file type '{content_type or 'unknown'}'. "
                "Allowed: JPEG, PNG, WebP."
            )

        filename = photo_storage.new_filename(content_type)

        async def chunks():
            while True:
                data = await upload.read(_CHUNK_SIZE)
                if not data:
                    break
                yield data

        try:
            size = await photo_storage.write_stream(
                request_id=request_id,
                filename=filename,
                chunks=chunks(),
                max_bytes=settings.MAX_PHOTO_SIZE_BYTES,
            )
        except photo_storage.PhotoTooLargeError as exc:
            raise ValidationError(
                f"File exceeds the {settings.MAX_PHOTO_SIZE_MB} MB limit"
            ) from exc

        photo = RequestPhoto(
            request_id=request_id,
            storage_path=photo_storage.relative_path(request_id, filename),
            content_type=content_type,
            size_bytes=size,
        )
        self.db.add(photo)
        await self.db.flush()
        return photo

    # -------------------------------------------------------------- read/serve
    async def get_file(
        self, request_id: uuid.UUID, photo_id: uuid.UUID, user: User
    ) -> tuple[Path, str]:
        """Return (absolute path, content type) after an access check.

        Access is gated by request ownership/role (via get_or_404), so a photo
        URL is useless without a token for someone allowed to see the request.
        """
        await self._get_request_owned(request_id, user)  # 404 if not allowed
        photo = await self._get_photo(request_id, photo_id)

        path = photo_storage.absolute_path(photo.storage_path)
        if not path.exists():
            raise NotFoundError("Photo file is missing on disk")
        return path, photo.content_type or "application/octet-stream"

    # ------------------------------------------------------------------ delete
    async def delete(
        self, request_id: uuid.UUID, photo_id: uuid.UUID, user: User
    ) -> None:
        req = await self._get_request_owned(request_id, user)
        if req.status in TERMINAL_STATES:
            raise ConflictError(
                f"Cannot modify photos of a {req.status.value} request"
            )
        photo = await self._get_photo(request_id, photo_id)

        storage_path = photo.storage_path
        await self.db.delete(photo)
        await self.db.commit()
        # Delete the file only after the row is gone, so a failed commit can't
        # orphan the DB from a deleted file.
        photo_storage.delete_file(storage_path)

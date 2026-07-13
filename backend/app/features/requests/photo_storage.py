"""Low-level photo storage on local disk (hackathon: no object storage).

Files live under ``settings.UPLOAD_DIR/requests/{request_id}/{uuid}.{ext}``.
Filenames are server-generated UUIDs — client filenames are never trusted, so
path traversal is impossible. This module knows nothing about the DB or HTTP;
the service layer orchestrates it alongside ``RequestPhoto`` rows.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from app.core.config import settings

# MIME -> canonical extension for the formats we accept.
EXTENSION_BY_MIME = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class PhotoTooLargeError(Exception):
    """Raised mid-stream when a file exceeds the per-file size cap."""


def _upload_root() -> Path:
    return Path(settings.UPLOAD_DIR)


def relative_path(request_id: uuid.UUID, filename: str) -> str:
    """Repo-relative storage path stored in the DB (portable across envs)."""
    return f"requests/{request_id}/{filename}"


def absolute_path(storage_path: str) -> Path:
    """Resolve a stored relative path to an absolute path, guarding traversal.

    Even though we generate the path ourselves, we re-verify the resolved path
    stays under the upload root — defense in depth against a tampered DB value.
    """
    root = _upload_root().resolve()
    resolved = (root / storage_path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Resolved path escapes the upload root")
    return resolved


def new_filename(content_type: str) -> str:
    """A random, non-guessable filename with the extension for this MIME type."""
    ext = EXTENSION_BY_MIME[content_type]
    return f"{uuid.uuid4().hex}.{ext}"


async def write_stream(
    *,
    request_id: uuid.UUID,
    filename: str,
    chunks,
    max_bytes: int,
) -> int:
    """Write an async byte-chunk iterator to disk atomically; return size.

    Streams to a ``.tmp`` sibling and renames on success, so a partial/failed
    write never leaves a half-file at the real path. Aborts (and cleans up) with
    ``PhotoTooLargeError`` the moment the running total exceeds ``max_bytes``.
    """
    dest = absolute_path(relative_path(request_id, filename))
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")

    total = 0
    try:
        with open(tmp, "wb") as fh:
            async for chunk in chunks:
                total += len(chunk)
                if total > max_bytes:
                    raise PhotoTooLargeError
                fh.write(chunk)
        os.replace(tmp, dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return total


def delete_file(storage_path: str) -> None:
    """Remove a stored file if present; missing file is not an error."""
    try:
        absolute_path(storage_path).unlink(missing_ok=True)
    except ValueError:
        # Path escaped the root (tampered value) — nothing safe to delete.
        pass

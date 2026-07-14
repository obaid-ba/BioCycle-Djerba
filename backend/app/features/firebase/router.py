"""Live camera feed endpoint.

Exposes the current Firebase camera state to the dashboard. Scoped: a hotel
manager sees it only if one of their hotels is linked to a camera
(firebase_device_id set); operators/admins see it if any camera is configured.
Read-only.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.features.auth.dependencies import CurrentUser
from app.features.auth.models import UserRole
from app.features.hotels.models import Hotel
from app.shared.exceptions import NotFoundError, ValidationError

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def _user_has_camera(db: AsyncSession, user) -> bool:
    """True if this user is allowed to see a camera feed.

    Hotel managers need a hotel with a firebase_device_id; staff can view if any
    hotel has a camera configured.
    """
    stmt = select(Hotel).where(Hotel.firebase_device_id.isnot(None))
    if user.role == UserRole.HOTEL_MANAGER:
        stmt = stmt.where(Hotel.manager_id == user.id)
    result = await db.execute(stmt.limit(1))
    return result.scalar_one_or_none() is not None


@router.get("/live", summary="Live camera detection summary (dashboard)")
async def live_camera(current_user: CurrentUser, db: DbSession) -> dict[str, Any]:
    if not settings.FIREBASE_ENABLED:
        raise ValidationError("Live camera feed is not enabled")

    # Only surface the feed to users linked to a camera — don't leak it broadly.
    if not await _user_has_camera(db, current_user):
        raise NotFoundError("No camera is linked to your account")

    # Imported here so the Firebase deps load only when the feed is used.
    from app.integrations.firebase.reader import FirebaseError, FirebaseRealtimeReader

    try:
        summary = await FirebaseRealtimeReader().get_live_summary()
    except FirebaseError as exc:
        # Surface a clean, non-500 error if the camera/Firebase is unreachable.
        raise ValidationError(f"Camera feed unavailable: {exc}") from exc
    return summary

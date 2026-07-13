"""Notification business logic.

Creates per-user notifications and pushes them live over the targeted WebSocket.
The DB write joins the caller's transaction (flush, no commit) so the notification
and the event that triggered it are atomic; the live push is best-effort and
happens after the caller commits (via `deliver`).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models import Notification, NotificationType
from app.features.notifications.repository import NotificationRepository
from app.features.notifications.schemas import NotificationRead
from app.realtime.events import build_notification_event
from app.realtime.manager import manager
from app.shared.exceptions import NotFoundError
from app.shared.schemas import Page, PaginationParams

# Map a terminal/decision request status to a notification type + copy.
# Only statuses the hotel cares about (decisions + completion) are here.
_STATUS_NOTIFICATIONS = {
    "accepted": (NotificationType.REQUEST_ACCEPTED, "Request accepted"),
    "rejected": (NotificationType.REQUEST_REJECTED, "Request rejected"),
    "completed": (NotificationType.REQUEST_COMPLETED, "Collection completed"),
}


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = NotificationRepository(db)

    # -------------------------------------------------------------- creation
    async def create_for_request_status(
        self,
        *,
        recipient_id: uuid.UUID,
        request_id: uuid.UUID,
        status_value: str,
        weight_kg: float,
    ) -> Notification | None:
        """Persist a notification for a request status change (flush, no commit).

        Returns the notification (so the caller can push it after commit), or
        None if this status isn't one the hotel is notified about.
        """
        mapping = _STATUS_NOTIFICATIONS.get(status_value)
        if mapping is None:
            return None
        ntype, title = mapping

        message = self._message_for(status_value, weight_kg)
        notification = Notification(
            user_id=recipient_id,
            type=ntype,
            title=title,
            message=message,
            request_id=request_id,
        )
        return await self.repo.add(notification)

    @staticmethod
    def _message_for(status_value: str, weight_kg: float) -> str:
        kg = f"{weight_kg:g} kg"
        if status_value == "accepted":
            return f"Your {kg} request was accepted and is scheduled for collection."
        if status_value == "rejected":
            return f"Your {kg} request was rejected. See details for the reason."
        if status_value == "completed":
            return f"Your {kg} request has been collected. Thank you!"
        return ""

    @staticmethod
    async def deliver(notification: Notification) -> None:
        """Push a persisted notification live to its recipient's connections.

        Best-effort: called after the caller commits. If the user is offline the
        notification still waits for them in the DB.
        """
        await manager.send_to_user(
            notification.user_id, build_notification_event(notification)
        )

    # ------------------------------------------------------------------ reads
    async def list(
        self, *, user_id: uuid.UUID, params: PaginationParams, unread_only: bool = False
    ) -> Page[NotificationRead]:
        items, total = await self.repo.list_for_user(
            user_id=user_id, params=params, unread_only=unread_only
        )
        return Page.create(
            [NotificationRead.model_validate(n) for n in items], total, params
        )

    async def unread_count(self, user_id: uuid.UUID) -> int:
        return await self.repo.unread_count(user_id)

    # ------------------------------------------------------------------ writes
    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
        notification = await self.repo.get(notification_id)
        # 404 (not 403) for someone else's notification — don't leak existence.
        if notification is None or notification.user_id != user_id:
            raise NotFoundError("Notification not found")
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            await self.db.flush()
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        count = await self.repo.mark_all_read(user_id, now=datetime.now(timezone.utc))
        await self.db.commit()
        return count

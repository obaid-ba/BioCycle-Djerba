"""Data access for notifications (always scoped to a single recipient)."""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select, update

from app.features.notifications.models import Notification
from app.shared.repository import BaseRepository
from app.shared.schemas import PaginationParams


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        params: PaginationParams,
        unread_only: bool = False,
    ) -> tuple[Sequence[Notification], int]:
        filters = [Notification.user_id == user_id]
        if unread_only:
            filters.append(Notification.is_read.is_(False))

        items = await self.list(
            offset=params.offset,
            limit=params.limit,
            order_by=Notification.created_at.desc(),
            filters=filters,
        )
        total = await self.count(filters=filters)
        return items, total

    async def unread_count(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.is_read.is_(False)
        )
        return int((await self.db.execute(stmt)).scalar_one())

    async def mark_all_read(self, user_id: uuid.UUID, *, now) -> int:
        """Mark every unread notification for the user as read; return the count."""
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True, read_at=now)
        )
        result = await self.db.execute(stmt)
        return int(result.rowcount or 0)

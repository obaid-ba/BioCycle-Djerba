"""Data access for activity logs."""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select

from app.features.activity.models import ActivityLog
from app.shared.repository import BaseRepository
from app.shared.schemas import PaginationParams


class ActivityLogRepository(BaseRepository[ActivityLog]):
    model = ActivityLog

    async def search(
        self,
        *,
        params: PaginationParams,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
    ) -> tuple[Sequence[ActivityLog], int]:
        stmt = select(ActivityLog)
        count_stmt = select(func.count()).select_from(ActivityLog)

        if user_id is not None:
            stmt = stmt.where(ActivityLog.user_id == user_id)
            count_stmt = count_stmt.where(ActivityLog.user_id == user_id)
        if action is not None:
            stmt = stmt.where(ActivityLog.action == action)
            count_stmt = count_stmt.where(ActivityLog.action == action)
        if entity_type is not None:
            stmt = stmt.where(ActivityLog.entity_type == entity_type)
            count_stmt = count_stmt.where(ActivityLog.entity_type == entity_type)

        stmt = (
            stmt.order_by(ActivityLog.created_at.desc()).offset(params.offset).limit(params.limit)
        )
        items = (await self.db.execute(stmt)).scalars().all()
        total = int((await self.db.execute(count_stmt)).scalar_one())
        return items, total

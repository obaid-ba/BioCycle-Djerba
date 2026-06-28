"""Activity logging service.

`record()` adds a log row and flushes but does NOT commit — it joins the
caller's transaction so the audit entry and the action it describes are
persisted atomically. Other features inject this service to record events.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.activity.models import ActivityLog
from app.features.activity.repository import ActivityLogRepository
from app.features.activity.schemas import ActivityLogRead
from app.features.auth.models import User
from app.shared.schemas import Page, PaginationParams


class ActivityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.logs = ActivityLogRepository(db)

    async def record(
        self,
        *,
        action: str,
        user: User | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        message: str | None = None,
        context: dict | None = None,
    ) -> ActivityLog:
        log = ActivityLog(
            user_id=user.id if user is not None else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            message=message,
            context=context,
        )
        return await self.logs.add(log)

    async def list(
        self,
        *,
        params: PaginationParams,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
    ) -> Page[ActivityLogRead]:
        items, total = await self.logs.search(
            params=params, user_id=user_id, action=action, entity_type=entity_type
        )
        return Page.create([ActivityLogRead.model_validate(log) for log in items], total, params)

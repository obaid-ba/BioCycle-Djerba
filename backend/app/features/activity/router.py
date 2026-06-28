"""Activity log HTTP layer (read-only; staff access)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.activity.schemas import ActivityLogRead
from app.features.activity.service import ActivityService
from app.features.auth.dependencies import require_role
from app.features.auth.models import UserRole
from app.shared.schemas import Page, PaginationParams, pagination_params

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends(pagination_params)]


@router.get(
    "",
    response_model=Page[ActivityLogRead],
    summary="List activity logs",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))],
)
async def list_activity(
    db: DbSession,
    params: Pagination,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    entity_type: str | None = None,
) -> Page[ActivityLogRead]:
    return await ActivityService(db).list(
        params=params, user_id=user_id, action=action, entity_type=entity_type
    )

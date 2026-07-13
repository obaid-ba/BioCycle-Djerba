"""Notification HTTP layer — thin handlers, always scoped to the current user."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.auth.dependencies import CurrentUser
from app.features.notifications.schemas import NotificationRead, UnreadCount
from app.features.notifications.service import NotificationService
from app.shared.schemas import Page, PaginationParams, pagination_params

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends(pagination_params)]


@router.get("", response_model=Page[NotificationRead], summary="My notifications")
async def list_notifications(
    current_user: CurrentUser,
    db: DbSession,
    params: Pagination,
    unread: Annotated[bool, Query(description="Only unread notifications")] = False,
) -> Page[NotificationRead]:
    return await NotificationService(db).list(
        user_id=current_user.id, params=params, unread_only=unread
    )


@router.get(
    "/unread-count", response_model=UnreadCount, summary="My unread notification count"
)
async def unread_count(current_user: CurrentUser, db: DbSession) -> UnreadCount:
    count = await NotificationService(db).unread_count(current_user.id)
    return UnreadCount(unread=count)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationRead,
    summary="Mark a notification read",
)
async def mark_read(
    notification_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> NotificationRead:
    notification = await NotificationService(db).mark_read(
        notification_id, current_user.id
    )
    return NotificationRead.model_validate(notification)


@router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark all my notifications read",
)
async def mark_all_read(current_user: CurrentUser, db: DbSession) -> None:
    await NotificationService(db).mark_all_read(current_user.id)

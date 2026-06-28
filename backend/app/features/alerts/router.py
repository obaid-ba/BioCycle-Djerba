"""Alert HTTP layer: list, get, manual create, acknowledge, resolve, delete."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.alerts.models import AlertSeverity, AlertStatus, AlertType
from app.features.alerts.schemas import AlertCreate, AlertRead
from app.features.alerts.service import AlertService
from app.features.auth.dependencies import CurrentUser, require_role
from app.features.auth.models import UserRole
from app.realtime.events import build_alert_event
from app.realtime.manager import manager
from app.shared.schemas import Page, PaginationParams, pagination_params

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends(pagination_params)]
StaffOnly = [Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))]
AdminOnly = [Depends(require_role(UserRole.ADMIN))]


@router.get("", response_model=Page[AlertRead], summary="List alerts")
async def list_alerts(
    current_user: CurrentUser,
    db: DbSession,
    params: Pagination,
    status_filter: Annotated[AlertStatus | None, Query(alias="status")] = None,
    severity: AlertSeverity | None = None,
    type_filter: Annotated[AlertType | None, Query(alias="type")] = None,
    hotel_id: uuid.UUID | None = None,
    bin_id: uuid.UUID | None = None,
    sort: Annotated[str | None, Query(description="e.g. '-created_at'")] = None,
) -> Page[AlertRead]:
    items, total = await AlertService(db).list(
        params=params,
        user=current_user,
        status=status_filter,
        severity=severity,
        type_=type_filter,
        hotel_id=hotel_id,
        bin_id=bin_id,
        sort=sort,
    )
    return Page.create([AlertRead.model_validate(a) for a in items], total, params)


@router.post(
    "",
    response_model=AlertRead,
    status_code=status.HTTP_201_CREATED,
    summary="Raise a manual alert",
    dependencies=StaffOnly,
)
async def create_alert(payload: AlertCreate, db: DbSession, current_user: CurrentUser) -> AlertRead:
    alert = await AlertService(db).create(payload, current_user)
    await manager.broadcast(build_alert_event(alert))
    return AlertRead.model_validate(alert)


@router.get("/{alert_id}", response_model=AlertRead, summary="Get an alert")
async def get_alert(alert_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> AlertRead:
    alert = await AlertService(db).get_or_404(alert_id, current_user)
    return AlertRead.model_validate(alert)


@router.post(
    "/{alert_id}/acknowledge",
    response_model=AlertRead,
    summary="Acknowledge an alert",
    dependencies=StaffOnly,
)
async def acknowledge_alert(
    alert_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> AlertRead:
    alert = await AlertService(db).acknowledge(alert_id, current_user)
    await manager.broadcast(build_alert_event(alert))
    return AlertRead.model_validate(alert)


@router.post(
    "/{alert_id}/resolve",
    response_model=AlertRead,
    summary="Resolve an alert",
    dependencies=StaffOnly,
)
async def resolve_alert(alert_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> AlertRead:
    alert = await AlertService(db).resolve(alert_id, current_user)
    await manager.broadcast(build_alert_event(alert))
    return AlertRead.model_validate(alert)


@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an alert (admin only)",
    dependencies=AdminOnly,
)
async def delete_alert(alert_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> None:
    await AlertService(db).delete(alert_id, current_user)

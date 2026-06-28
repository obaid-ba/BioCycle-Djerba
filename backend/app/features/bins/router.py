"""Smart bin HTTP layer: bin CRUD plus nested sensor-reading routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.auth.dependencies import CurrentUser, require_role
from app.features.auth.models import UserRole
from app.features.bins.models import BinStatus, BinType
from app.features.bins.schemas import (
    SensorReadingCreate,
    SensorReadingRead,
    SmartBinCreate,
    SmartBinRead,
    SmartBinUpdate,
)
from app.features.bins.service import BinService
from app.shared.schemas import Page, PaginationParams, pagination_params

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends(pagination_params)]
StaffOnly = [Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))]
AdminOnly = [Depends(require_role(UserRole.ADMIN))]


@router.get("", response_model=Page[SmartBinRead], summary="List smart bins")
async def list_bins(
    current_user: CurrentUser,
    db: DbSession,
    params: Pagination,
    search: Annotated[str | None, Query(description="Match code or name")] = None,
    hotel_id: uuid.UUID | None = None,
    status_filter: Annotated[BinStatus | None, Query(alias="status")] = None,
    bin_type: BinType | None = None,
    sort: Annotated[str | None, Query(description="e.g. 'code' or '-fill_level'")] = None,
) -> Page[SmartBinRead]:
    return await BinService(db).list(
        params=params,
        user=current_user,
        search=search,
        hotel_id=hotel_id,
        status=status_filter,
        bin_type=bin_type,
        sort=sort,
    )


@router.post(
    "",
    response_model=SmartBinRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a smart bin",
    dependencies=StaffOnly,
)
async def create_bin(
    payload: SmartBinCreate, db: DbSession, current_user: CurrentUser
) -> SmartBinRead:
    bin_ = await BinService(db).create(payload, current_user)
    return SmartBinRead.model_validate(bin_)


@router.get("/{bin_id}", response_model=SmartBinRead, summary="Get a smart bin")
async def get_bin(bin_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> SmartBinRead:
    bin_ = await BinService(db).get_or_404(bin_id, current_user)
    return SmartBinRead.model_validate(bin_)


@router.patch(
    "/{bin_id}",
    response_model=SmartBinRead,
    summary="Update a smart bin",
    dependencies=StaffOnly,
)
async def update_bin(
    bin_id: uuid.UUID,
    payload: SmartBinUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> SmartBinRead:
    bin_ = await BinService(db).update(bin_id, payload, current_user)
    return SmartBinRead.model_validate(bin_)


@router.delete(
    "/{bin_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a smart bin (admin only)",
    dependencies=AdminOnly,
)
async def delete_bin(bin_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> None:
    await BinService(db).delete(bin_id, current_user)


@router.get(
    "/{bin_id}/readings",
    response_model=Page[SensorReadingRead],
    summary="List a bin's sensor readings",
)
async def list_readings(
    bin_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    params: Pagination,
) -> Page[SensorReadingRead]:
    return await BinService(db).list_readings(bin_id, params, current_user)


@router.get(
    "/{bin_id}/latest",
    response_model=SensorReadingRead,
    summary="Latest reading for a bin",
)
async def latest_reading(
    bin_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> SensorReadingRead:
    reading = await BinService(db).latest_reading(bin_id, current_user)
    return SensorReadingRead.model_validate(reading)


@router.post(
    "/{bin_id}/readings",
    response_model=SensorReadingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a sensor reading (also used to simulate devices)",
    dependencies=StaffOnly,
)
async def ingest_reading(
    bin_id: uuid.UUID, payload: SensorReadingCreate, db: DbSession
) -> SensorReadingRead:
    reading = await BinService(db).ingest_reading(bin_id, payload)
    return SensorReadingRead.model_validate(reading)

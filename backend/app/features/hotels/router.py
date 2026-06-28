"""Hotel HTTP layer — full CRUD with pagination, search, filter, and sort."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.auth.dependencies import CurrentUser, require_role
from app.features.auth.models import UserRole
from app.features.hotels.models import HotelStatus
from app.features.hotels.schemas import HotelCreate, HotelRead, HotelUpdate
from app.features.hotels.service import HotelService
from app.shared.schemas import Page, PaginationParams, pagination_params

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends(pagination_params)]


@router.get("", response_model=Page[HotelRead], summary="List hotels")
async def list_hotels(
    current_user: CurrentUser,
    db: DbSession,
    params: Pagination,
    search: Annotated[str | None, Query(description="Match name or city")] = None,
    status_filter: Annotated[HotelStatus | None, Query(alias="status")] = None,
    sort: Annotated[str | None, Query(description="e.g. 'name' or '-created_at'")] = None,
) -> Page[HotelRead]:
    return await HotelService(db).list(
        params=params,
        user=current_user,
        search=search,
        status=status_filter,
        sort=sort,
    )


@router.post(
    "",
    response_model=HotelRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a hotel",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))],
)
async def create_hotel(payload: HotelCreate, db: DbSession, current_user: CurrentUser) -> HotelRead:
    hotel = await HotelService(db).create(payload, current_user)
    return HotelRead.model_validate(hotel)


@router.get("/{hotel_id}", response_model=HotelRead, summary="Get a hotel")
async def get_hotel(hotel_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> HotelRead:
    hotel = await HotelService(db).get_or_404(hotel_id, current_user)
    return HotelRead.model_validate(hotel)


@router.patch(
    "/{hotel_id}",
    response_model=HotelRead,
    summary="Update a hotel",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))],
)
async def update_hotel(
    hotel_id: uuid.UUID,
    payload: HotelUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> HotelRead:
    hotel = await HotelService(db).update(hotel_id, payload, current_user)
    return HotelRead.model_validate(hotel)


@router.delete(
    "/{hotel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a hotel (admin only)",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_hotel(hotel_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> None:
    await HotelService(db).delete(hotel_id, current_user)

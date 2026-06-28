"""Waste collection HTTP layer: CRUD plus AI prediction routes."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.auth.dependencies import CurrentUser, require_role
from app.features.auth.models import UserRole
from app.features.collections.schemas import (
    PredictionRead,
    WasteCollectionCreate,
    WasteCollectionRead,
    WasteCollectionUpdate,
)
from app.features.collections.service import CollectionService
from app.integrations.ai_service import AIServiceClient, get_ai_client
from app.shared.schemas import Page, PaginationParams, pagination_params

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends(pagination_params)]
AIClient = Annotated[AIServiceClient, Depends(get_ai_client)]
StaffOnly = [Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))]
AdminOnly = [Depends(require_role(UserRole.ADMIN))]


@router.get("", response_model=Page[WasteCollectionRead], summary="List collections")
async def list_collections(
    current_user: CurrentUser,
    db: DbSession,
    params: Pagination,
    hotel_id: uuid.UUID | None = None,
    bin_id: uuid.UUID | None = None,
    date_from: Annotated[datetime | None, Query(description="collected_at >=")] = None,
    date_to: Annotated[datetime | None, Query(description="collected_at <=")] = None,
    sort: Annotated[str | None, Query(description="e.g. '-collected_at'")] = None,
) -> Page[WasteCollectionRead]:
    return await CollectionService(db).list(
        params=params,
        user=current_user,
        hotel_id=hotel_id,
        bin_id=bin_id,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
    )


@router.post(
    "",
    response_model=WasteCollectionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record a waste collection",
    dependencies=StaffOnly,
)
async def create_collection(
    payload: WasteCollectionCreate, db: DbSession, current_user: CurrentUser
) -> WasteCollectionRead:
    collection = await CollectionService(db).create(payload, current_user)
    return WasteCollectionRead.model_validate(collection)


@router.get(
    "/{collection_id}",
    response_model=WasteCollectionRead,
    summary="Get a collection",
)
async def get_collection(
    collection_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> WasteCollectionRead:
    collection = await CollectionService(db).get_or_404(collection_id, current_user)
    return WasteCollectionRead.model_validate(collection)


@router.patch(
    "/{collection_id}",
    response_model=WasteCollectionRead,
    summary="Update a collection",
    dependencies=StaffOnly,
)
async def update_collection(
    collection_id: uuid.UUID,
    payload: WasteCollectionUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> WasteCollectionRead:
    collection = await CollectionService(db).update(collection_id, payload, current_user)
    return WasteCollectionRead.model_validate(collection)


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a collection (admin only)",
    dependencies=AdminOnly,
)
async def delete_collection(
    collection_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> None:
    await CollectionService(db).delete(collection_id, current_user)


@router.post(
    "/{collection_id}/predictions",
    response_model=PredictionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Request an AI energy prediction for a collection",
    dependencies=StaffOnly,
)
async def create_prediction(
    collection_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    ai_client: AIClient,
) -> PredictionRead:
    prediction = await CollectionService(db).predict(collection_id, current_user, ai_client)
    return PredictionRead.model_validate(prediction)


@router.get(
    "/{collection_id}/predictions",
    response_model=Page[PredictionRead],
    summary="List predictions for a collection",
)
async def list_predictions(
    collection_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    params: Pagination,
) -> Page[PredictionRead]:
    return await CollectionService(db).list_predictions(collection_id, params, current_user)


@router.get(
    "/{collection_id}/predictions/latest",
    response_model=PredictionRead,
    summary="Latest prediction for a collection",
)
async def latest_prediction(
    collection_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> PredictionRead:
    prediction = await CollectionService(db).latest_prediction(collection_id, current_user)
    return PredictionRead.model_validate(prediction)

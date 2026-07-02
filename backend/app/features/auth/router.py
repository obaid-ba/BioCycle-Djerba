"""Auth HTTP layer — thin handlers delegating to AuthService."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.auth.dependencies import CurrentUser, require_role
from app.features.auth.models import UserRole
from app.features.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.features.auth.service import AuthService
from app.shared.schemas import Page, PaginationParams, pagination_params

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends(pagination_params)]
AdminOnly = [Depends(require_role(UserRole.ADMIN))]


@router.post("/login", response_model=TokenResponse, summary="Authenticate and get tokens")
async def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    return await AuthService(db).login(payload.email, payload.password)


@router.post("/refresh", response_model=TokenResponse, summary="Exchange refresh for access")
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenResponse:
    return await AuthService(db).refresh(payload.refresh_token)


@router.get("/me", response_model=UserRead, summary="Current authenticated user")
async def read_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get(
    "/users",
    response_model=Page[UserRead],
    summary="List users (admin only)",
    dependencies=AdminOnly,
)
async def list_users(db: DbSession, params: Pagination) -> Page[UserRead]:
    items, total = await AuthService(db).list_users(params)
    return Page.create([UserRead.model_validate(u) for u in items], total, params)


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user (admin only)",
    dependencies=AdminOnly,
)
async def create_user(payload: UserCreate, db: DbSession) -> UserRead:
    user = await AuthService(db).register(payload)
    return UserRead.model_validate(user)


@router.patch(
    "/users/{user_id}",
    response_model=UserRead,
    summary="Update a user (admin only)",
    dependencies=AdminOnly,
)
async def update_user(user_id: uuid.UUID, payload: UserUpdate, db: DbSession) -> UserRead:
    user = await AuthService(db).update_user(user_id, payload)
    return UserRead.model_validate(user)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user (admin only)",
    dependencies=AdminOnly,
)
async def delete_user(user_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> None:
    await AuthService(db).delete_user(user_id, current_user)

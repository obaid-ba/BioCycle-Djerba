"""Auth HTTP layer — thin handlers delegating to AuthService."""

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
)
from app.features.auth.service import AuthService

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/login", response_model=TokenResponse, summary="Authenticate and get tokens")
async def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    return await AuthService(db).login(payload.email, payload.password)


@router.post("/refresh", response_model=TokenResponse, summary="Exchange refresh for access")
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenResponse:
    return await AuthService(db).refresh(payload.refresh_token)


@router.get("/me", response_model=UserRead, summary="Current authenticated user")
async def read_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user (admin only)",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def create_user(payload: UserCreate, db: DbSession) -> UserRead:
    user = await AuthService(db).register(payload)
    return UserRead.model_validate(user)

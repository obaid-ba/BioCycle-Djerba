"""Auth DTOs — the public request/response contracts for the auth feature."""

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.features.auth.models import UserRole
from app.shared.schemas import BaseSchema


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseSchema):
    refresh_token: str


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class UserCreate(BaseSchema):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.HOTEL_MANAGER


class UserUpdate(BaseSchema):
    """Admin edit of a user — all fields optional (PATCH semantics)."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserRead(BaseSchema):
    id: uuid.UUID
    # Plain str on the read path: emails are validated with EmailStr on input
    # (login/create). Re-validating already-persisted values on output would let
    # one legacy/edge-case address (e.g. a reserved-TLD dev seed) 500 the whole
    # list endpoint.
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

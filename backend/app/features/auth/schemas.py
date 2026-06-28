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


class UserRead(BaseSchema):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

"""Authentication business logic.

The service owns the transaction boundary (`commit`) and all auth rules; the
router stays thin and the repository stays query-only.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.features.auth.models import User
from app.features.auth.repository import UserRepository
from app.features.auth.schemas import TokenResponse, UserCreate
from app.shared.exceptions import ConflictError, UnauthorizedError


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        # Verify against the hash even when the user is missing would be ideal to
        # avoid timing leaks; kept simple here, revisit if it becomes a concern.
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is disabled")
        return user

    def _issue_tokens(self, user: User) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(str(user.id), user.role.value),
            refresh_token=create_refresh_token(str(user.id)),
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.authenticate(email, password)
        return self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if payload.get("type") != TOKEN_TYPE_REFRESH:
            raise UnauthorizedError("Invalid token type")
        user = await self.users.get(uuid.UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or inactive")
        return self._issue_tokens(user)

    async def register(self, data: UserCreate) -> User:
        if await self.users.get_by_email(data.email) is not None:
            raise ConflictError("A user with this email already exists")
        user = User(
            email=data.email,
            full_name=data.full_name,
            role=data.role,
            hashed_password=hash_password(data.password),
        )
        user = await self.users.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

"""Authentication business logic.

The service owns the transaction boundary (`commit`) and all auth rules; the
router stays thin and the repository stays query-only.
"""

import uuid
from collections.abc import Sequence

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
from app.features.auth.schemas import TokenResponse, UserCreate, UserUpdate
from app.shared.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.shared.schemas import PaginationParams


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

    async def list_users(self, params: PaginationParams) -> tuple[Sequence[User], int]:
        items = await self.users.list(offset=params.offset, limit=params.limit)
        total = await self.users.count()
        return items, total

    async def get_or_404(self, user_id: uuid.UUID) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def update_user(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        user = await self.get_or_404(user_id)
        if data.full_name is not None:
            user.full_name = data.full_name
        if data.role is not None:
            user.role = data.role
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.password is not None:
            user.hashed_password = hash_password(data.password)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete_user(self, user_id: uuid.UUID, current_user: User) -> None:
        if user_id == current_user.id:
            raise ForbiddenError("You cannot delete your own account")
        user = await self.get_or_404(user_id)
        await self.users.delete(user)
        await self.db.commit()

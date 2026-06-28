"""Auth dependencies: current-user resolution and role-based guards.

These are the building blocks every protected route reuses. `CurrentUser` is an
annotated shortcut; `require_role(...)` returns a dependency that enforces RBAC.
"""

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.features.auth.models import User, UserRole
from app.features.auth.repository import UserRepository
from app.shared.exceptions import ForbiddenError, UnauthorizedError

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Missing authentication token")

    payload = decode_token(credentials.credentials)
    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise UnauthorizedError("Invalid token type")

    subject = payload.get("sub")
    if subject is None:
        raise UnauthorizedError("Malformed token")

    user = await UserRepository(db).get(uuid.UUID(subject))
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole):
    """Return a dependency that allows only the given roles."""

    async def role_checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError("You do not have permission to access this resource")
        return user

    return role_checker

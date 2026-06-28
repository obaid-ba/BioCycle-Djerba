"""Idempotently create the initial admin user.

Run after migrations:  python -m scripts.seed_admin
Reads credentials from FIRST_SUPERUSER_* settings.
"""

import asyncio

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.features.auth.models import User, UserRole
from app.features.auth.repository import UserRepository


async def seed_admin() -> None:
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        if await repo.get_by_email(settings.FIRST_SUPERUSER_EMAIL) is not None:
            print(f"Admin '{settings.FIRST_SUPERUSER_EMAIL}' already exists — skipping.")
            return

        admin = User(
            email=settings.FIRST_SUPERUSER_EMAIL,
            full_name=settings.FIRST_SUPERUSER_NAME,
            role=UserRole.ADMIN,
            hashed_password=hash_password(settings.FIRST_SUPERUSER_PASSWORD),
        )
        await repo.add(admin)
        await db.commit()
        print(f"Created admin '{settings.FIRST_SUPERUSER_EMAIL}'.")


if __name__ == "__main__":
    asyncio.run(seed_admin())

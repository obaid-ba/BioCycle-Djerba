"""Shared pytest fixtures.

Tests run against an in-memory SQLite database via the same async session
machinery as production, with `get_db` overridden. This keeps tests fast and
hermetic — no Postgres required for unit/integration tests of the app layer.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import hash_password
from app.features.auth.models import User, UserRole
from app.features.hotels.models import Hotel, HotelStatus
from app.main import app
from app.shared.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db_session: AsyncSession):
    """Factory fixture that inserts a user into the test DB."""

    async def _make_user(
        *,
        email: str = "user@test.io",
        password: str = "password123",
        full_name: str = "Test User",
        role: UserRole = UserRole.HOTEL_MANAGER,
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email,
            full_name=full_name,
            role=role,
            hashed_password=hash_password(password),
            is_active=is_active,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _make_user


@pytest.fixture
def login(client: AsyncClient):
    """Log in an existing user and return ready-to-use auth headers."""

    async def _login(email: str, password: str = "password123") -> dict[str, str]:
        response = await client.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login


@pytest.fixture
def auth_headers(make_user, login):
    """Create a user with a given role and return its auth headers."""

    async def _auth_headers(
        role: UserRole = UserRole.ADMIN, email: str | None = None
    ) -> dict[str, str]:
        email = email or f"{role.value}@test.io"
        await make_user(email=email, password="password123", role=role)
        return await login(email)

    return _auth_headers


@pytest.fixture
def make_hotel(db_session: AsyncSession):
    """Factory fixture that inserts a hotel into the test DB."""

    async def _make_hotel(
        *,
        name: str = "Test Hotel",
        city: str = "Djerba",
        status: HotelStatus = HotelStatus.ACTIVE,
        manager_id=None,
        **kwargs,
    ) -> Hotel:
        hotel = Hotel(name=name, city=city, status=status, manager_id=manager_id, **kwargs)
        db_session.add(hotel)
        await db_session.commit()
        await db_session.refresh(hotel)
        return hotel

    return _make_hotel

"""Shared pytest fixtures.

Tests run against a shared in-memory SQLite database (StaticPool keeps the single
connection alive across sessions). Crucially, each HTTP request gets its OWN
session via `get_db` — exactly like production — so we exercise realistic
session-per-request semantics instead of one long-lived session.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.features.auth.models import User, UserRole
from app.features.bins.models import BinStatus, BinType, SmartBin
from app.features.hotels.models import Hotel, HotelStatus
from app.main import app
from app.shared.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def engine() -> AsyncGenerator:
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# Data factories — each opens a short-lived session, commits, and returns the
# persisted entity. They share the same in-memory DB as the request sessions.
# --------------------------------------------------------------------------- #


@pytest.fixture
def make_user(session_factory):
    async def _make_user(
        *,
        email: str = "user@test.io",
        password: str = "password123",
        full_name: str = "Test User",
        role: UserRole = UserRole.HOTEL_MANAGER,
        is_active: bool = True,
    ) -> User:
        async with session_factory() as session:
            user = User(
                email=email,
                full_name=full_name,
                role=role,
                hashed_password=hash_password(password),
                is_active=is_active,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
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
def make_hotel(session_factory):
    async def _make_hotel(
        *,
        name: str = "Test Hotel",
        city: str = "Djerba",
        status: HotelStatus = HotelStatus.ACTIVE,
        manager_id=None,
        **kwargs,
    ) -> Hotel:
        async with session_factory() as session:
            hotel = Hotel(name=name, city=city, status=status, manager_id=manager_id, **kwargs)
            session.add(hotel)
            await session.commit()
            await session.refresh(hotel)
            return hotel

    return _make_hotel


@pytest.fixture
def make_bin(session_factory):
    async def _make_bin(
        *,
        hotel_id,
        code: str = "BIN-001",
        name: str = "Test Bin",
        bin_type: BinType = BinType.MIXED,
        status: BinStatus = BinStatus.OFFLINE,
        **kwargs,
    ) -> SmartBin:
        async with session_factory() as session:
            bin_ = SmartBin(
                hotel_id=hotel_id,
                code=code,
                name=name,
                bin_type=bin_type,
                status=status,
                **kwargs,
            )
            session.add(bin_)
            await session.commit()
            await session.refresh(bin_)
            return bin_

    return _make_bin

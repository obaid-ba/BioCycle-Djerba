"""Auth feature integration tests: login, refresh, /me, and RBAC."""

from collections.abc import Callable
from typing import Any

from httpx import AsyncClient

from app.features.auth.models import UserRole


async def _login(client: AsyncClient, email: str, password: str) -> dict[str, Any]:
    response = await client.post("/api/auth/login", json={"email": email, "password": password})
    return response


async def test_login_success(client: AsyncClient, make_user: Callable) -> None:
    await make_user(email="ops@test.io", password="password123", role=UserRole.OPERATOR)

    response = await _login(client, "ops@test.io", "password123")

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["expires_in"] > 0


async def test_login_wrong_password(client: AsyncClient, make_user: Callable) -> None:
    await make_user(email="ops@test.io", password="password123")

    response = await _login(client, "ops@test.io", "wrong-password")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_me_returns_current_user(client: AsyncClient, make_user: Callable) -> None:
    await make_user(email="me@test.io", password="password123", full_name="Mee")
    token = (await _login(client, "me@test.io", "password123")).json()["access_token"]

    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "me@test.io"
    assert response.json()["full_name"] == "Mee"


async def test_refresh_issues_new_access_token(client: AsyncClient, make_user: Callable) -> None:
    await make_user(email="r@test.io", password="password123")
    refresh_token = (await _login(client, "r@test.io", "password123")).json()["refresh_token"]

    response = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_refresh_rejects_access_token(client: AsyncClient, make_user: Callable) -> None:
    await make_user(email="r2@test.io", password="password123")
    access_token = (await _login(client, "r2@test.io", "password123")).json()["access_token"]

    response = await client.post("/api/auth/refresh", json={"refresh_token": access_token})

    assert response.status_code == 401


async def test_create_user_forbidden_for_non_admin(
    client: AsyncClient, make_user: Callable
) -> None:
    await make_user(email="hm@test.io", password="password123", role=UserRole.HOTEL_MANAGER)
    token = (await _login(client, "hm@test.io", "password123")).json()["access_token"]

    response = await client.post(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "new@test.io",
            "full_name": "New User",
            "password": "password123",
            "role": "operator",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_create_user_allowed_for_admin(client: AsyncClient, make_user: Callable) -> None:
    await make_user(email="admin@test.io", password="password123", role=UserRole.ADMIN)
    token = (await _login(client, "admin@test.io", "password123")).json()["access_token"]

    response = await client.post(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "fresh@test.io",
            "full_name": "Fresh User",
            "password": "password123",
            "role": "operator",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "fresh@test.io"
    assert response.json()["role"] == "operator"


async def test_create_duplicate_user_conflicts(client: AsyncClient, make_user: Callable) -> None:
    await make_user(email="admin@test.io", password="password123", role=UserRole.ADMIN)
    token = (await _login(client, "admin@test.io", "password123")).json()["access_token"]

    payload = {
        "email": "dup@test.io",
        "full_name": "Dup",
        "password": "password123",
        "role": "operator",
    }
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/auth/users", headers=headers, json=payload)
    response = await client.post("/api/auth/users", headers=headers, json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"

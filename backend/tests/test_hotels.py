"""Hotel CRUD integration tests: RBAC, scoping, validation, list features."""

from collections.abc import Callable

from httpx import AsyncClient

from app.features.auth.models import UserRole

NEW_HOTEL = {
    "name": "Radisson Blu",
    "city": "Djerba",
    "country": "Tunisia",
    "latitude": 33.85,
    "longitude": 10.9,
    "status": "active",
}


async def test_create_hotel_as_admin(client: AsyncClient, auth_headers: Callable) -> None:
    headers = await auth_headers(UserRole.ADMIN)

    response = await client.post("/api/hotels", headers=headers, json=NEW_HOTEL)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Radisson Blu"
    assert body["status"] == "active"
    assert body["id"]


async def test_create_hotel_forbidden_for_manager(
    client: AsyncClient, auth_headers: Callable
) -> None:
    headers = await auth_headers(UserRole.HOTEL_MANAGER)

    response = await client.post("/api/hotels", headers=headers, json=NEW_HOTEL)

    assert response.status_code == 403


async def test_create_hotel_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/api/hotels", json=NEW_HOTEL)
    assert response.status_code == 401


async def test_create_hotel_invalid_manager(client: AsyncClient, auth_headers: Callable) -> None:
    headers = await auth_headers(UserRole.ADMIN)
    payload = {**NEW_HOTEL, "manager_id": "00000000-0000-0000-0000-000000000000"}

    response = await client.post("/api/hotels", headers=headers, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_create_hotel_invalid_latitude(client: AsyncClient, auth_headers: Callable) -> None:
    headers = await auth_headers(UserRole.ADMIN)
    payload = {**NEW_HOTEL, "latitude": 200}

    response = await client.post("/api/hotels", headers=headers, json=payload)

    assert response.status_code == 422


async def test_manager_only_sees_own_hotels(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    manager = await make_user(email="owner@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Owned", manager_id=manager.id)
    await make_hotel(name="Someone Else", manager_id=None)
    headers = await login("owner@test.io")

    response = await client.get("/api/hotels", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Owned"


async def test_operator_sees_all_hotels(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    await make_hotel(name="A")
    await make_hotel(name="B")
    headers = await auth_headers(UserRole.OPERATOR)

    response = await client.get("/api/hotels", headers=headers)

    assert response.status_code == 200
    assert response.json()["total"] == 2


async def test_get_hotel_not_found(client: AsyncClient, auth_headers: Callable) -> None:
    headers = await auth_headers(UserRole.ADMIN)

    response = await client.get("/api/hotels/00000000-0000-0000-0000-000000000000", headers=headers)

    assert response.status_code == 404


async def test_manager_get_other_hotel_returns_404(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    await make_user(email="owner@test.io", role=UserRole.HOTEL_MANAGER)
    other = await make_hotel(name="Not Mine", manager_id=None)
    headers = await login("owner@test.io")

    response = await client.get(f"/api/hotels/{other.id}", headers=headers)

    assert response.status_code == 404


async def test_update_hotel_as_operator(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel(name="Old Name")
    headers = await auth_headers(UserRole.OPERATOR)

    response = await client.patch(
        f"/api/hotels/{hotel.id}", headers=headers, json={"name": "New Name"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


async def test_delete_hotel_forbidden_for_operator(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    headers = await auth_headers(UserRole.OPERATOR)

    response = await client.delete(f"/api/hotels/{hotel.id}", headers=headers)

    assert response.status_code == 403


async def test_delete_hotel_as_admin(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    headers = await auth_headers(UserRole.ADMIN)

    response = await client.delete(f"/api/hotels/{hotel.id}", headers=headers)

    assert response.status_code == 204

    follow_up = await client.get(f"/api/hotels/{hotel.id}", headers=headers)
    assert follow_up.status_code == 404


async def test_search_filters_by_name(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    await make_hotel(name="Seabel Aladin", city="Djerba")
    await make_hotel(name="Iberostar", city="Hammamet")
    headers = await auth_headers(UserRole.ADMIN)

    response = await client.get("/api/hotels?search=aladin", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Seabel Aladin"


async def test_pagination_and_sort(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    for name in ["Charlie", "Alpha", "Bravo"]:
        await make_hotel(name=name)
    headers = await auth_headers(UserRole.ADMIN)

    response = await client.get("/api/hotels?sort=name&page=1&page_size=2", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert [h["name"] for h in body["items"]] == ["Alpha", "Bravo"]


async def test_invalid_sort_field_rejected(client: AsyncClient, auth_headers: Callable) -> None:
    headers = await auth_headers(UserRole.ADMIN)

    response = await client.get("/api/hotels?sort=hacker", headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"

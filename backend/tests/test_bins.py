"""Smart bin + sensor reading integration tests."""

from collections.abc import Callable

from httpx import AsyncClient

from app.features.auth.models import UserRole


async def test_create_bin_as_admin(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    headers = await auth_headers(UserRole.ADMIN)

    response = await client.post(
        "/api/bins",
        headers=headers,
        json={"code": "ESP32-01", "name": "Lobby Bin", "hotel_id": str(hotel.id)},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "ESP32-01"
    assert body["status"] == "offline"
    assert body["hotel_id"] == str(hotel.id)


async def test_create_bin_forbidden_for_manager(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    headers = await auth_headers(UserRole.HOTEL_MANAGER)

    response = await client.post(
        "/api/bins",
        headers=headers,
        json={"code": "ESP32-02", "hotel_id": str(hotel.id)},
    )

    assert response.status_code == 403


async def test_create_bin_invalid_hotel(client: AsyncClient, auth_headers: Callable) -> None:
    headers = await auth_headers(UserRole.ADMIN)

    response = await client.post(
        "/api/bins",
        headers=headers,
        json={"code": "ESP32-03", "hotel_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_create_duplicate_code_conflicts(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    await make_bin(hotel_id=hotel.id, code="DUP-1")
    headers = await auth_headers(UserRole.ADMIN)

    response = await client.post(
        "/api/bins",
        headers=headers,
        json={"code": "DUP-1", "hotel_id": str(hotel.id)},
    )

    assert response.status_code == 409


async def test_manager_only_sees_own_hotel_bins(
    client: AsyncClient,
    make_user: Callable,
    make_hotel: Callable,
    make_bin: Callable,
    login: Callable,
) -> None:
    manager = await make_user(email="owner@test.io", role=UserRole.HOTEL_MANAGER)
    mine = await make_hotel(name="Mine", manager_id=manager.id)
    theirs = await make_hotel(name="Theirs", manager_id=None)
    await make_bin(hotel_id=mine.id, code="MINE-1")
    await make_bin(hotel_id=theirs.id, code="THEIRS-1")
    headers = await login("owner@test.io")

    response = await client.get("/api/bins", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["code"] == "MINE-1"


async def test_filter_bins_by_hotel(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    a = await make_hotel(name="A")
    b = await make_hotel(name="B")
    await make_bin(hotel_id=a.id, code="A-1")
    await make_bin(hotel_id=b.id, code="B-1")
    headers = await auth_headers(UserRole.OPERATOR)

    response = await client.get(f"/api/bins?hotel_id={a.id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["code"] == "A-1"


async def test_update_bin_as_operator(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    bin_ = await make_bin(hotel_id=hotel.id, code="UPD-1")
    headers = await auth_headers(UserRole.OPERATOR)

    response = await client.patch(f"/api/bins/{bin_.id}", headers=headers, json={"name": "Renamed"})

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


async def test_delete_bin_admin_only(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    bin_ = await make_bin(hotel_id=hotel.id, code="DEL-1")

    operator = await auth_headers(UserRole.OPERATOR)
    assert (await client.delete(f"/api/bins/{bin_.id}", headers=operator)).status_code == 403

    admin = await auth_headers(UserRole.ADMIN)
    assert (await client.delete(f"/api/bins/{bin_.id}", headers=admin)).status_code == 204


async def test_ingest_reading_updates_bin_state(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    bin_ = await make_bin(hotel_id=hotel.id, code="ING-1")
    headers = await auth_headers(UserRole.ADMIN)

    ingest = await client.post(
        f"/api/bins/{bin_.id}/readings",
        headers=headers,
        json={
            "fill_level": 75.5,
            "battery_level": 88,
            "temperature_c": 31.2,
            "humidity": 60,
        },
    )
    assert ingest.status_code == 201

    bin_state = (await client.get(f"/api/bins/{bin_.id}", headers=headers)).json()
    assert bin_state["fill_level"] == 75.5
    assert bin_state["battery_level"] == 88
    assert bin_state["status"] == "online"
    assert bin_state["last_reading_at"] is not None

    latest = (await client.get(f"/api/bins/{bin_.id}/latest", headers=headers)).json()
    assert latest["fill_level"] == 75.5
    assert latest["temperature_c"] == 31.2


async def test_latest_reading_404_when_empty(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    bin_ = await make_bin(hotel_id=hotel.id, code="EMPTY-1")
    headers = await auth_headers(UserRole.ADMIN)

    response = await client.get(f"/api/bins/{bin_.id}/latest", headers=headers)

    assert response.status_code == 404


async def test_readings_history_ordered_desc(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    bin_ = await make_bin(hotel_id=hotel.id, code="HIST-1")
    headers = await auth_headers(UserRole.ADMIN)

    for fill, ts in [
        (10, "2026-06-28T10:00:00Z"),
        (20, "2026-06-28T11:00:00Z"),
        (30, "2026-06-28T12:00:00Z"),
    ]:
        await client.post(
            f"/api/bins/{bin_.id}/readings",
            headers=headers,
            json={"fill_level": fill, "recorded_at": ts},
        )

    response = await client.get(f"/api/bins/{bin_.id}/readings", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert [r["fill_level"] for r in body["items"]] == [30, 20, 10]


async def test_invalid_fill_level_rejected(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    bin_ = await make_bin(hotel_id=hotel.id, code="BAD-1")
    headers = await auth_headers(UserRole.ADMIN)

    response = await client.post(
        f"/api/bins/{bin_.id}/readings",
        headers=headers,
        json={"fill_level": 150},
    )

    assert response.status_code == 422

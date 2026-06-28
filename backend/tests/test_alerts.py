"""Alert tests: auto-rules engine, dedup, lifecycle, RBAC, scoping."""

from collections.abc import Callable

from httpx import AsyncClient

from app.features.auth.models import UserRole


async def _ingest(client, headers, bin_id, **payload):
    return await client.post(f"/api/bins/{bin_id}/readings", headers=headers, json=payload)


async def test_high_fill_raises_warning_alert(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    bin_ = await make_bin(hotel_id=hotel.id, code="AL-1")
    headers = await auth_headers(UserRole.ADMIN)

    await _ingest(client, headers, bin_.id, fill_level=92)

    alerts = (await client.get("/api/alerts", headers=headers)).json()
    assert alerts["total"] == 1
    assert alerts["items"][0]["type"] == "bin_full"
    assert alerts["items"][0]["severity"] == "warning"


async def test_critical_fill_raises_critical_alert(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    bin_ = await make_bin(hotel_id=hotel.id, code="AL-2")
    headers = await auth_headers(UserRole.ADMIN)

    await _ingest(client, headers, bin_.id, fill_level=98)

    alerts = (await client.get("/api/alerts", headers=headers)).json()
    assert alerts["items"][0]["severity"] == "critical"


async def test_alerts_are_deduplicated(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    bin_ = await make_bin(hotel_id=hotel.id, code="AL-3")
    headers = await auth_headers(UserRole.ADMIN)

    await _ingest(client, headers, bin_.id, fill_level=90)
    await _ingest(client, headers, bin_.id, fill_level=93)
    await _ingest(client, headers, bin_.id, fill_level=96)

    alerts = (await client.get("/api/alerts", headers=headers)).json()
    assert alerts["total"] == 1


async def test_low_battery_raises_alert(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    bin_ = await make_bin(hotel_id=hotel.id, code="AL-4")
    headers = await auth_headers(UserRole.ADMIN)

    await _ingest(client, headers, bin_.id, fill_level=10, battery_level=5)

    alerts = (await client.get("/api/alerts?type=bin_battery_low", headers=headers)).json()
    assert alerts["total"] == 1


async def test_manual_alert_create_rbac(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    payload = {"hotel_id": str(hotel.id), "title": "Inspection due", "severity": "info"}

    manager = await auth_headers(UserRole.HOTEL_MANAGER)
    assert (await client.post("/api/alerts", headers=manager, json=payload)).status_code == 403

    admin = await auth_headers(UserRole.ADMIN)
    created = await client.post("/api/alerts", headers=admin, json=payload)
    assert created.status_code == 201
    assert created.json()["status"] == "open"


async def test_acknowledge_and_resolve_lifecycle(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    bin_ = await make_bin(hotel_id=hotel.id, code="AL-5")
    headers = await auth_headers(UserRole.OPERATOR)
    await _ingest(client, headers, bin_.id, fill_level=99)
    alert_id = (await client.get("/api/alerts", headers=headers)).json()["items"][0]["id"]

    ack = await client.post(f"/api/alerts/{alert_id}/acknowledge", headers=headers)
    assert ack.status_code == 200
    assert ack.json()["status"] == "acknowledged"
    assert ack.json()["acknowledged_by"] is not None

    resolved = await client.post(f"/api/alerts/{alert_id}/resolve", headers=headers)
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolved_at"] is not None


async def test_manager_only_sees_own_hotel_alerts(
    client: AsyncClient,
    make_user: Callable,
    make_hotel: Callable,
    make_bin: Callable,
    auth_headers: Callable,
    login: Callable,
) -> None:
    manager = await make_user(email="owner@test.io", role=UserRole.HOTEL_MANAGER)
    mine = await make_hotel(name="Mine", manager_id=manager.id)
    theirs = await make_hotel(name="Theirs")
    bin_mine = await make_bin(hotel_id=mine.id, code="M-1")
    bin_theirs = await make_bin(hotel_id=theirs.id, code="T-1")

    admin = await auth_headers(UserRole.ADMIN)
    await _ingest(client, admin, bin_mine.id, fill_level=95)
    await _ingest(client, admin, bin_theirs.id, fill_level=95)

    manager_headers = await login("owner@test.io")
    alerts = (await client.get("/api/alerts", headers=manager_headers)).json()
    assert alerts["total"] == 1
    assert alerts["items"][0]["hotel_id"] == str(mine.id)

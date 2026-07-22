"""Tests for the operator request map payload.

The operator's request view draws the hotel -> plant leg. That needs three
things to travel with the request: the hotel's identity/coordinates, the plant's
coordinates, and the distance between them — all consistent with each other.
"""

from collections.abc import Callable

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.features.auth.models import UserRole
from app.shared.geo import haversine_km

# A real Djerba hotel position (Radisson Blu, Sidi Mahrez).
HOTEL_LAT, HOTEL_LNG = 33.8869, 10.9639


async def _request_from_placed_hotel(
    make_user, make_hotel, login, client, *, lat=HOTEL_LAT, lng=HOTEL_LNG
):
    manager = await make_user(email="mapmgr@test.io", role=UserRole.HOTEL_MANAGER)
    hotel = await make_hotel(
        name="Radisson Blu Palace",
        city="Midoun",
        manager_id=manager.id,
        latitude=lat,
        longitude=lng,
    )
    headers = await login("mapmgr@test.io")
    resp = await client.post(
        "/api/requests", headers=headers, json={"declared_containers": 4}
    )
    assert resp.status_code == 201, resp.text
    return resp.json(), hotel


async def test_request_embeds_hotel_and_plant_coordinates(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    """The map can be drawn from a single request payload — no extra fetch."""
    body, hotel = await _request_from_placed_hotel(
        make_user, make_hotel, login, client
    )

    assert body["hotel"]["id"] == str(hotel.id)
    assert body["hotel"]["name"] == "Radisson Blu Palace"
    assert body["hotel"]["latitude"] == pytest.approx(HOTEL_LAT)
    assert body["hotel"]["longitude"] == pytest.approx(HOTEL_LNG)

    assert body["plant_latitude"] == pytest.approx(settings.PLANT_LATITUDE)
    assert body["plant_longitude"] == pytest.approx(settings.PLANT_LONGITUDE)


async def test_distance_matches_the_two_plotted_points(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    """The label the operator reads must match the leg the map draws.

    Guards the real risk: plant coords drifting apart from the snapshotted
    `distance_to_plant_km`, which would show a distance contradicting the line.
    """
    body, _ = await _request_from_placed_hotel(make_user, make_hotel, login, client)

    expected = haversine_km(
        body["hotel"]["latitude"],
        body["hotel"]["longitude"],
        body["plant_latitude"],
        body["plant_longitude"],
    )
    assert body["distance_to_plant_km"] == pytest.approx(expected, abs=0.01)


async def test_hotel_without_coordinates_yields_null_distance(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    """An unplaced hotel still serializes; the UI falls back to an empty state."""
    manager = await make_user(email="nogeo@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Unplaced Hotel", manager_id=manager.id)
    headers = await login("nogeo@test.io")

    resp = await client.post(
        "/api/requests", headers=headers, json={"declared_containers": 2}
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["distance_to_plant_km"] is None
    assert body["hotel"]["latitude"] is None
    # Plant coords are still served — only the hotel end is missing.
    assert body["plant_latitude"] == pytest.approx(settings.PLANT_LATITUDE)


async def test_operator_queue_rows_carry_hotel_identity(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    """The queue list — not just the detail endpoint — names each hotel."""
    await _request_from_placed_hotel(make_user, make_hotel, login, client)
    await make_user(email="op@test.io", role=UserRole.OPERATOR)
    op_headers = await login("op@test.io")

    resp = await client.get("/api/requests", headers=op_headers)

    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["hotel"]["name"] == "Radisson Blu Palace"
    assert items[0]["hotel"]["city"] == "Midoun"

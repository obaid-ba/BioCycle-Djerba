"""Dashboard stats & analytics tests (LEGACY, waste_collections-based).

SKIPPED: this whole module targets the old dashboard/analytics surface built
on waste_collections (fed via the now-unmounted /collections API). The current,
request-centric analytics are covered by test_request_analytics.py.
"""

from collections.abc import Callable

import pytest
from httpx import AsyncClient

from app.features.auth.models import UserRole
from app.integrations.ai_service import get_ai_client

pytestmark = pytest.mark.skip(reason="legacy waste_collections analytics; see test_request_analytics.py")
from app.main import app


class FakeAIClient:
    def __init__(self, response: dict | None = None):
        self._response = response or {
            "predicted_energy_kwh": 100,
            "predicted_biogas_m3": 25,
            "co2_saved_kg": 40,
        }

    async def predict(self, payload: dict) -> dict:
        return self._response

    async def health(self) -> bool:
        return True


def _use_ai() -> None:
    app.dependency_overrides[get_ai_client] = lambda: FakeAIClient()


async def _add_collection(client, headers, hotel_id, organic=80, non_organic=20):
    return await client.post(
        "/api/collections",
        headers=headers,
        json={
            "hotel_id": str(hotel_id),
            "organic_weight_kg": organic,
            "non_organic_weight_kg": non_organic,
        },
    )


async def test_dashboard_stats(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    _use_ai()
    admin = await auth_headers(UserRole.ADMIN)
    hotel = await make_hotel()
    bin_ = await make_bin(hotel_id=hotel.id, code="D-1")
    await _add_collection(client, admin, hotel.id)
    await client.post(f"/api/bins/{bin_.id}/readings", headers=admin, json={"fill_level": 50})

    stats = (await client.get("/api/dashboard/stats", headers=admin)).json()

    assert stats["today_collections"] == 1
    assert stats["organic_waste_kg"] == 80
    assert stats["total_waste_kg"] == 100
    assert stats["hotels_connected"] == 1
    assert stats["total_bins"] == 1
    assert stats["online_bins"] == 1
    assert stats["system"]["ai"] == "online"
    assert stats["system"]["mqtt"] in {"online", "offline", "disabled"}


async def test_dashboard_includes_predicted_energy(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    _use_ai()
    admin = await auth_headers(UserRole.ADMIN)
    hotel = await make_hotel()
    collection_id = (await _add_collection(client, admin, hotel.id)).json()["id"]
    await client.post(f"/api/collections/{collection_id}/predictions", headers=admin)

    stats = (await client.get("/api/dashboard/stats", headers=admin)).json()

    assert stats["predicted_energy_kwh"] == 100
    assert stats["co2_saved_kg"] == 40


async def test_waste_distribution(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    admin = await auth_headers(UserRole.ADMIN)
    hotel = await make_hotel()
    await _add_collection(client, admin, hotel.id, organic=80, non_organic=20)
    await _add_collection(client, admin, hotel.id, organic=40, non_organic=60)

    dist = (await client.get("/api/analytics/waste-distribution", headers=admin)).json()

    assert dist["organic_kg"] == 120
    assert dist["non_organic_kg"] == 80
    assert dist["total_kg"] == 200
    assert dist["organic_percentage"] == 60.0


async def test_timeseries_day_gap_filled(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    admin = await auth_headers(UserRole.ADMIN)
    hotel = await make_hotel()
    await _add_collection(client, admin, hotel.id)

    buckets = (await client.get("/api/analytics/timeseries?granularity=day", headers=admin)).json()

    assert len(buckets) == 7  # last 7 days, gap-filled
    assert sum(b["count"] for b in buckets) == 1
    assert sum(b["total_kg"] for b in buckets) == 100


async def test_export_csv(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    admin = await auth_headers(UserRole.ADMIN)
    hotel = await make_hotel()
    await _add_collection(client, admin, hotel.id)

    response = await client.get("/api/analytics/export", headers=admin)

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "organic_weight_kg" in response.text
    assert response.text.count("\n") >= 2  # header + at least one row


async def test_dashboard_scoped_for_manager(
    client: AsyncClient,
    make_user: Callable,
    make_hotel: Callable,
    auth_headers: Callable,
    login: Callable,
) -> None:
    _use_ai()
    manager = await make_user(email="owner@test.io", role=UserRole.HOTEL_MANAGER)
    mine = await make_hotel(name="Mine", manager_id=manager.id)
    theirs = await make_hotel(name="Theirs")
    admin = await auth_headers(UserRole.ADMIN)
    await _add_collection(client, admin, mine.id)
    await _add_collection(client, admin, theirs.id)

    manager_headers = await login("owner@test.io")
    stats = (await client.get("/api/dashboard/stats", headers=manager_headers)).json()

    assert stats["today_collections"] == 1
    assert stats["hotels_connected"] == 1

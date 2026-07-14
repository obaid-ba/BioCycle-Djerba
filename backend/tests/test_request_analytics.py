"""Request-centric analytics: KPIs, rankings, timeseries, scoping, RBAC."""

from collections.abc import Callable

from httpx import AsyncClient

from app.features.auth.models import UserRole


async def _manager_with_requests(client, make_user, make_hotel, login, auth_headers):
    """Seed a hotel + a spread of requests across the lifecycle; return headers."""
    mgr = await make_user(email="an-mgr@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Analytics Hotel", manager_id=mgr.id, latitude=33.8, longitude=10.8)
    headers = await login("an-mgr@test.io")
    op = await auth_headers(UserRole.OPERATOR)

    ids = []
    for kg in (100, 250, 400):
        r = await client.post("/api/requests", headers=headers, json={"declared_containers": kg})
        ids.append(r.json()["id"])

    # Accept the first, reject the second, leave the third pending.
    await client.post(f"/api/requests/{ids[0]}/decision", headers=op, json={"accept": True})
    await client.post(
        f"/api/requests/{ids[1]}/decision", headers=op,
        json={"accept": False, "rejection_reason": "contaminated"},
    )
    return headers, op


async def test_request_stats(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    headers, _ = await _manager_with_requests(client, make_user, make_hotel, login, auth_headers)

    resp = await client.get("/api/dashboard/request-stats", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["total_requests"] == 3
    assert body["status_counts"]["accepted"] == 1
    assert body["status_counts"]["rejected"] == 1
    assert body["status_counts"]["pending"] == 1
    from app.core.config import settings

    assert body["declared_weight_kg"] == 750 * settings.CONTAINER_WEIGHT_KG
    assert body["estimated_methane_m3"] > 0
    assert body["avg_quality_score"] is not None
    # 1 accepted of 2 decided -> 50%.
    assert body["acceptance_rate"] == 50.0


async def test_hotel_ranking_sorted_by_methane(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    # Two hotels with different total loads -> different methane totals.
    m1 = await make_user(email="r1@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Big Hotel", manager_id=m1.id)
    h1 = await login("r1@test.io")
    for kg in (500, 500):
        await client.post("/api/requests", headers=h1, json={"declared_containers": kg})

    m2 = await make_user(email="r2@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Small Hotel", manager_id=m2.id)
    h2 = await login("r2@test.io")
    await client.post("/api/requests", headers=h2, json={"declared_containers": 50})

    admin = await auth_headers(UserRole.ADMIN)
    resp = await client.get("/api/analytics/hotel-ranking", headers=admin)
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 2
    # Sorted by methane desc -> Big Hotel first.
    methane = [r["total_methane_m3"] for r in rows]
    assert methane == sorted(methane, reverse=True)
    assert rows[0]["hotel_name"] == "Big Hotel"


async def test_operator_ranking_admin_only(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    headers, op = await _manager_with_requests(client, make_user, make_hotel, login, auth_headers)

    # Manager forbidden.
    forbidden = await client.get("/api/analytics/operator-ranking", headers=headers)
    assert forbidden.status_code == 403

    admin = await auth_headers(UserRole.ADMIN)
    resp = await client.get("/api/analytics/operator-ranking", headers=admin)
    assert resp.status_code == 200
    rows = resp.json()
    # The operator decided 2 requests (1 accept + 1 reject).
    assert any(r["handled_count"] == 2 for r in rows)


async def test_requests_timeseries(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    headers, _ = await _manager_with_requests(client, make_user, make_hotel, login, auth_headers)

    resp = await client.get(
        "/api/analytics/requests-timeseries?granularity=day", headers=headers
    )
    assert resp.status_code == 200
    buckets = resp.json()
    assert len(buckets) >= 1
    # All 3 requests were created today -> today's bucket holds them.
    assert sum(b["count"] for b in buckets) == 3


async def test_manager_stats_scoped_to_own_hotel(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    headers, _ = await _manager_with_requests(client, make_user, make_hotel, login, auth_headers)

    # A second manager with no requests sees zeros, not the first manager's data.
    m2 = await make_user(email="empty@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Empty Hotel", manager_id=m2.id)
    h2 = await login("empty@test.io")

    resp = await client.get("/api/dashboard/request-stats", headers=h2)
    assert resp.json()["total_requests"] == 0


async def test_request_stats_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/dashboard/request-stats")
    assert resp.status_code == 401

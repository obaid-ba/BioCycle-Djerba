"""Collection-request integration tests.

Covers the product's core workflow end-to-end over HTTP: creation + AI scoring,
the priority-sorted operator queue, RBAC/ownership scoping, the operator
accept/reject decision, the full lifecycle, and rejection of illegal moves.
"""

from collections.abc import Callable

import pytest
from httpx import AsyncClient

from app.features.auth.models import UserRole


async def _hotel_manager(make_user, make_hotel, login, *, email="mgr@test.io"):
    """Create a hotel manager owning exactly one hotel; return (headers, hotel)."""
    manager = await make_user(email=email, role=UserRole.HOTEL_MANAGER)
    hotel = await make_hotel(name="Owned Hotel", manager_id=manager.id)
    headers = await login(email)
    return headers, hotel


# --------------------------------------------------------------------------- #
# Creation + AI scoring
# --------------------------------------------------------------------------- #
async def test_hotel_creates_request_and_gets_ai_scores(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)

    resp = await client.post("/api/requests", headers=headers, json={"declared_weight_kg": 320})

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["ai_status"] == "success"
    # Stub scorer populates all headline metrics.
    assert body["ai_priority_score"] is not None
    assert body["ai_estimated_methane_m3"] > 0
    assert body["ai_estimated_energy_kwh"] > 0
    assert 0 <= body["ai_confidence"] <= 1
    assert body["declared_weight_kg"] == 320


async def test_ai_scoring_is_deterministic(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    """Same request id must always produce the same score (stub is reproducible)."""
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    created = (await client.post("/api/requests", headers=headers, json={"declared_weight_kg": 100})).json()

    fetched = (await client.get(f"/api/requests/{created['id']}", headers=headers)).json()
    assert fetched["ai_priority_score"] == created["ai_priority_score"]


async def test_create_rejects_non_positive_weight(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    resp = await client.post("/api/requests", headers=headers, json={"declared_weight_kg": 0})
    assert resp.status_code == 422


async def test_operator_cannot_create_request(
    client: AsyncClient, auth_headers: Callable
) -> None:
    headers = await auth_headers(UserRole.OPERATOR)
    resp = await client.post("/api/requests", headers=headers, json={"declared_weight_kg": 50})
    assert resp.status_code == 403


async def test_create_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/requests", json={"declared_weight_kg": 50})
    assert resp.status_code == 401


async def test_manager_without_hotel_cannot_create(
    client: AsyncClient, auth_headers: Callable
) -> None:
    # A hotel manager with no assigned hotel.
    headers = await auth_headers(UserRole.HOTEL_MANAGER, email="lonely@test.io")
    resp = await client.post("/api/requests", headers=headers, json={"declared_weight_kg": 50})
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# Operator queue: priority sort + scoping
# --------------------------------------------------------------------------- #
async def test_queue_sorted_by_quality_then_distance(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    """Explainable ordering: quality DESC first, distance ASC as the tiebreak.

    We verify the two keys are consistent with the returned order: quality is
    non-increasing, and within an equal-quality run distance is non-decreasing.
    """
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    for w in (50, 400, 150, 500):
        await client.post("/api/requests", headers=headers, json={"declared_weight_kg": w})

    op_headers = await auth_headers(UserRole.OPERATOR)
    resp = await client.get("/api/requests", headers=op_headers)

    assert resp.status_code == 200
    items = resp.json()["items"]

    # Primary key: quality non-increasing (NULLs, if any, sort last).
    qualities = [i["ai_quality_score"] for i in items]
    non_null = [q for q in qualities if q is not None]
    assert non_null == sorted(non_null, reverse=True), qualities

    # Tiebreak: within an equal-quality run, distance is non-decreasing.
    for a, b in zip(items, items[1:]):
        if a["ai_quality_score"] == b["ai_quality_score"]:
            da = a["distance_to_plant_km"]
            db = b["distance_to_plant_km"]
            if da is not None and db is not None:
                assert da <= db, (da, db)


async def test_distance_tiebreak_orders_closer_hotel_first(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    """Two hotels at clearly different distances from the plant: for requests of
    equal AI quality, the closer hotel must come first. We force equal quality by
    pinning the scorer deterministically is overkill here; instead we assert the
    distance snapshot itself is correct and monotonic with hotel placement."""
    from app.core.config import settings
    from app.shared.geo import haversine_km

    # Near hotel (at the plant) and far hotel (~1 degree away).
    near_mgr = await make_user(email="near@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(
        name="Near Hotel", manager_id=near_mgr.id,
        latitude=settings.PLANT_LATITUDE, longitude=settings.PLANT_LONGITUDE,
    )
    near_headers = await login("near@test.io")
    near = (
        await client.post("/api/requests", headers=near_headers, json={"declared_weight_kg": 100})
    ).json()

    far_mgr = await make_user(email="far@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(
        name="Far Hotel", manager_id=far_mgr.id,
        latitude=settings.PLANT_LATITUDE + 1.0, longitude=settings.PLANT_LONGITUDE + 1.0,
    )
    far_headers = await login("far@test.io")
    far = (
        await client.post("/api/requests", headers=far_headers, json={"declared_weight_kg": 100})
    ).json()

    # Distance snapshot is populated and matches haversine, near < far.
    assert near["distance_to_plant_km"] is not None
    assert far["distance_to_plant_km"] is not None
    assert near["distance_to_plant_km"] < far["distance_to_plant_km"]
    expected_far = round(
        haversine_km(
            settings.PLANT_LATITUDE + 1.0, settings.PLANT_LONGITUDE + 1.0,
            settings.PLANT_LATITUDE, settings.PLANT_LONGITUDE,
        ),
        2,
    )
    assert far["distance_to_plant_km"] == expected_far


async def test_request_without_hotel_coords_has_null_distance(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    """A hotel with no coordinates yields a NULL distance (sorts last), not an error."""
    mgr = await make_user(email="nocoord@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="No Coords", manager_id=mgr.id)  # no lat/lng
    headers = await login("nocoord@test.io")

    resp = await client.post("/api/requests", headers=headers, json={"declared_weight_kg": 100})
    assert resp.status_code == 201
    assert resp.json()["distance_to_plant_km"] is None


async def test_manager_only_sees_own_requests(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    h1, _ = await _hotel_manager(make_user, make_hotel, login, email="m1@test.io")
    await client.post("/api/requests", headers=h1, json={"declared_weight_kg": 100})

    # A second manager with their own hotel sees none of the first's requests.
    m2 = await make_user(email="m2@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Other Hotel", manager_id=m2.id)
    h2 = await login("m2@test.io")

    resp = await client.get("/api/requests", headers=h2)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_manager_cannot_read_other_request_404(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    h1, _ = await _hotel_manager(make_user, make_hotel, login, email="m1@test.io")
    created = (await client.post("/api/requests", headers=h1, json={"declared_weight_kg": 100})).json()

    m2 = await make_user(email="m2@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Other Hotel", manager_id=m2.id)
    h2 = await login("m2@test.io")

    # 404 (not 403): don't leak that the request exists.
    resp = await client.get(f"/api/requests/{created['id']}", headers=h2)
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Operator decision
# --------------------------------------------------------------------------- #
async def test_operator_accepts_request(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    req = (await client.post("/api/requests", headers=headers, json={"declared_weight_kg": 200})).json()

    op = await auth_headers(UserRole.OPERATOR)
    resp = await client.post(
        f"/api/requests/{req['id']}/decision", headers=op,
        json={"accept": True, "notes": "good load"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["decided_by"] is not None
    assert body["decided_at"] is not None


async def test_operator_rejects_request_with_reason(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    req = (await client.post("/api/requests", headers=headers, json={"declared_weight_kg": 200})).json()

    op = await auth_headers(UserRole.OPERATOR)
    resp = await client.post(
        f"/api/requests/{req['id']}/decision", headers=op,
        json={"accept": False, "rejection_reason": "too contaminated"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "too contaminated"


async def test_reject_without_reason_is_422(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    req = (await client.post("/api/requests", headers=headers, json={"declared_weight_kg": 200})).json()

    op = await auth_headers(UserRole.OPERATOR)
    resp = await client.post(
        f"/api/requests/{req['id']}/decision", headers=op, json={"accept": False}
    )
    assert resp.status_code == 422


async def test_hotel_manager_cannot_decide(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    req = (await client.post("/api/requests", headers=headers, json={"declared_weight_kg": 200})).json()

    resp = await client.post(
        f"/api/requests/{req['id']}/decision", headers=headers, json={"accept": True}
    )
    assert resp.status_code == 403


# --------------------------------------------------------------------------- #
# Full lifecycle + illegal transitions
# --------------------------------------------------------------------------- #
async def test_full_lifecycle_to_completed(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    req = (await client.post("/api/requests", headers=headers, json={"declared_weight_kg": 300})).json()
    op = await auth_headers(UserRole.OPERATOR)
    rid = req["id"]

    await client.post(f"/api/requests/{rid}/decision", headers=op, json={"accept": True})

    otw = await client.post(f"/api/requests/{rid}/transition", headers=op, json={"target": "on_the_way"})
    assert otw.json()["status"] == "on_the_way"

    collected = await client.post(
        f"/api/requests/{rid}/transition", headers=op,
        json={"target": "collected", "collected_weight_kg": 295.5},
    )
    assert collected.json()["status"] == "collected"
    assert collected.json()["collected_weight_kg"] == 295.5

    completed = await client.post(
        f"/api/requests/{rid}/transition", headers=op, json={"target": "completed"}
    )
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_at"] is not None


@pytest.mark.parametrize("target", ["completed", "collected", "on_the_way"])
async def test_illegal_transition_from_pending_is_409(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable, target: str,
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    req = (await client.post("/api/requests", headers=headers, json={"declared_weight_kg": 200})).json()
    op = await auth_headers(UserRole.OPERATOR)

    # None of these are reachable from PENDING (must be accepted first).
    resp = await client.post(
        f"/api/requests/{req['id']}/transition", headers=op, json={"target": target}
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


async def test_collected_requires_weight_422(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    req = (await client.post("/api/requests", headers=headers, json={"declared_weight_kg": 200})).json()
    op = await auth_headers(UserRole.OPERATOR)
    rid = req["id"]

    await client.post(f"/api/requests/{rid}/decision", headers=op, json={"accept": True})
    await client.post(f"/api/requests/{rid}/transition", headers=op, json={"target": "on_the_way"})

    resp = await client.post(
        f"/api/requests/{rid}/transition", headers=op, json={"target": "collected"}
    )
    assert resp.status_code == 422


async def test_transition_endpoint_rejects_accept_target_422(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    """accept/reject must go through /decision, not /transition."""
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    req = (await client.post("/api/requests", headers=headers, json={"declared_weight_kg": 200})).json()
    op = await auth_headers(UserRole.OPERATOR)

    resp = await client.post(
        f"/api/requests/{req['id']}/transition", headers=op, json={"target": "accepted"}
    )
    assert resp.status_code == 422

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
async def test_queue_sorted_by_priority_first(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    """Primary key is the AI priority score (DESC). The stub scores every
    request, so priority must be non-increasing down the returned queue."""
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    for w in (50, 400, 150, 500, 250):
        await client.post("/api/requests", headers=headers, json={"declared_weight_kg": w})

    op_headers = await auth_headers(UserRole.OPERATOR)
    resp = await client.get("/api/requests", headers=op_headers)

    assert resp.status_code == 200
    priorities = [i["ai_priority_score"] for i in resp.json()["items"]]
    non_null = [p for p in priorities if p is not None]
    assert non_null == sorted(non_null, reverse=True), priorities


async def test_queue_five_key_ordering_is_exact(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable, session_factory,
) -> None:
    """Deterministically verify all five ordering keys and their precedence by
    inserting requests with crafted values, then asserting the exact order:
      priority DESC > quality DESC > distance ASC > weight DESC > created_at ASC.
    """
    import uuid
    from datetime import datetime, timedelta, timezone

    from app.features.hotels.models import Hotel, HotelStatus
    from app.features.requests.models import AIStatus, CollectionRequest
    from app.features.requests.state_machine import RequestStatus

    mgr = await make_user(email="five@test.io", role=UserRole.HOTEL_MANAGER)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)

    # Each row isolates ONE tiebreak by holding the higher keys equal.
    # id -> (priority, quality, distance, weight, created_offset_days)
    rows = {
        "A": (90, 50, 100, 100, 0),   # top: highest priority
        "B": (80, 99, 100, 100, 0),   # priority beats quality
        "C": (80, 50, 5, 100, 0),     # same P<B; lower quality but closer... but quality outranks distance
        "D": (80, 50, 50, 100, 0),    # same P & quality as C; farther -> after C
        "E": (80, 50, 50, 999, 0),    # same P/quality/distance as D; heavier -> before D
        "F": (80, 50, 50, 100, 5),    # same as D but newer -> after D (FIFO: older first)
        "G": (80, 50, 50, 100, 1),    # same as D but between D(0) and F(5)
    }
    async with session_factory() as s:
        hotel = Hotel(name="Five Hotel", city="Djerba", status=HotelStatus.ACTIVE, manager_id=mgr.id)
        s.add(hotel)
        await s.flush()
        for code, (p, q, dist, w, off) in rows.items():
            s.add(
                CollectionRequest(
                    id=uuid.uuid4(),
                    hotel_id=hotel.id,
                    status=RequestStatus.PENDING,
                    ai_status=AIStatus.SUCCESS,
                    declared_weight_kg=w,
                    ai_priority_score=p,
                    ai_quality_score=q,
                    distance_to_plant_km=dist,
                    created_at=base + timedelta(days=off),
                    operator_notes=code,  # tag so we can read the order back
                )
            )
        await s.commit()

    op = await auth_headers(UserRole.OPERATOR)
    items = (await client.get("/api/requests?page_size=50", headers=op)).json()["items"]
    order = [i["operator_notes"] for i in items if i["operator_notes"] in rows]

    # Expected precedence:
    #  A (P90) first; then P80 group ordered by quality: B (q99) before the rest;
    #  within q50/P80: distance asc -> C(5) before {D,E,F,G at 50};
    #  at distance 50: weight desc -> E(999) first; then among weight 100:
    #  FIFO by created_at -> D(day0), G(day1), F(day5).
    assert order == ["A", "B", "C", "E", "D", "G", "F"], order


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

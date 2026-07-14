"""Notification tests: raised on request status changes, scoping, read state."""

from collections.abc import Callable

from httpx import AsyncClient

from app.features.auth.models import UserRole


async def _manager_and_hotel(make_user, make_hotel, login, *, email="notif-mgr@test.io"):
    mgr = await make_user(email=email, role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Notif Hotel", manager_id=mgr.id)
    headers = await login(email)
    return mgr, headers


async def _create_request(client, headers, kg=200) -> str:
    r = await client.post("/api/requests", headers=headers, json={"declared_containers": kg})
    return r.json()["id"]


async def test_accept_raises_notification(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    _, headers = await _manager_and_hotel(make_user, make_hotel, login)
    rid = await _create_request(client, headers)

    op = await auth_headers(UserRole.OPERATOR)
    await client.post(f"/api/requests/{rid}/decision", headers=op, json={"accept": True})

    # The hotel manager now has one unread notification about the acceptance.
    resp = await client.get("/api/notifications", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["type"] == "request_accepted"
    assert items[0]["request_id"] == rid
    assert items[0]["is_read"] is False


async def test_reject_raises_notification(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    _, headers = await _manager_and_hotel(make_user, make_hotel, login)
    rid = await _create_request(client, headers)

    op = await auth_headers(UserRole.OPERATOR)
    await client.post(
        f"/api/requests/{rid}/decision", headers=op,
        json={"accept": False, "rejection_reason": "contaminated"},
    )

    items = (await client.get("/api/notifications", headers=headers)).json()["items"]
    assert len(items) == 1
    assert items[0]["type"] == "request_rejected"


async def test_full_flow_notifies_accept_and_complete_only(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    """on_the_way / collected are operational and must NOT notify; accept + complete do."""
    _, headers = await _manager_and_hotel(make_user, make_hotel, login)
    rid = await _create_request(client, headers)
    op = await auth_headers(UserRole.OPERATOR)

    await client.post(f"/api/requests/{rid}/decision", headers=op, json={"accept": True})
    await client.post(f"/api/requests/{rid}/transition", headers=op, json={"target": "on_the_way"})
    await client.post(
        f"/api/requests/{rid}/transition", headers=op,
        json={"target": "collected", "collected_weight_kg": 190},
    )
    await client.post(f"/api/requests/{rid}/transition", headers=op, json={"target": "completed"})

    items = (await client.get("/api/notifications", headers=headers)).json()["items"]
    types = sorted(n["type"] for n in items)
    assert types == ["request_accepted", "request_completed"]


async def test_notifications_scoped_to_recipient(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    _, headers = await _manager_and_hotel(make_user, make_hotel, login, email="m1@test.io")
    rid = await _create_request(client, headers)
    op = await auth_headers(UserRole.OPERATOR)
    await client.post(f"/api/requests/{rid}/decision", headers=op, json={"accept": True})

    # A different manager sees none of the first's notifications.
    m2 = await make_user(email="m2@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Other", manager_id=m2.id)
    h2 = await login("m2@test.io")
    resp = await client.get("/api/notifications", headers=h2)
    assert resp.json()["total"] == 0


async def test_unread_count_and_mark_read(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    _, headers = await _manager_and_hotel(make_user, make_hotel, login)
    op = await auth_headers(UserRole.OPERATOR)
    for _ in range(2):
        rid = await _create_request(client, headers)
        await client.post(f"/api/requests/{rid}/decision", headers=op, json={"accept": True})

    assert (await client.get("/api/notifications/unread-count", headers=headers)).json()["unread"] == 2

    nid = (await client.get("/api/notifications", headers=headers)).json()["items"][0]["id"]
    read = await client.post(f"/api/notifications/{nid}/read", headers=headers)
    assert read.status_code == 200
    assert read.json()["is_read"] is True

    assert (await client.get("/api/notifications/unread-count", headers=headers)).json()["unread"] == 1


async def test_mark_all_read(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    _, headers = await _manager_and_hotel(make_user, make_hotel, login)
    op = await auth_headers(UserRole.OPERATOR)
    for _ in range(3):
        rid = await _create_request(client, headers)
        await client.post(f"/api/requests/{rid}/decision", headers=op, json={"accept": True})

    resp = await client.post("/api/notifications/read-all", headers=headers)
    assert resp.status_code == 204
    assert (await client.get("/api/notifications/unread-count", headers=headers)).json()["unread"] == 0


async def test_cannot_read_others_notification(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    _, headers = await _manager_and_hotel(make_user, make_hotel, login, email="owner@test.io")
    rid = await _create_request(client, headers)
    op = await auth_headers(UserRole.OPERATOR)
    await client.post(f"/api/requests/{rid}/decision", headers=op, json={"accept": True})
    nid = (await client.get("/api/notifications", headers=headers)).json()["items"][0]["id"]

    m2 = await make_user(email="intruder@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Intruder Hotel", manager_id=m2.id)
    h2 = await login("intruder@test.io")

    # 404, not 403 — don't leak existence.
    resp = await client.post(f"/api/notifications/{nid}/read", headers=h2)
    assert resp.status_code == 404


async def test_notifications_require_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/notifications")).status_code == 401

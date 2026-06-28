"""Activity log tests: audit recording and access control."""

from collections.abc import Callable

from httpx import AsyncClient

from app.features.auth.models import UserRole


async def test_hotel_creation_is_audited(client: AsyncClient, auth_headers: Callable) -> None:
    headers = await auth_headers(UserRole.ADMIN)
    await client.post(
        "/api/hotels", headers=headers, json={"name": "Audited Hotel", "city": "Djerba"}
    )

    logs = (await client.get("/api/activity-logs", headers=headers)).json()
    actions = [log["action"] for log in logs["items"]]
    assert "hotel.created" in actions


async def test_collection_creation_is_audited(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    headers = await auth_headers(UserRole.OPERATOR)
    await client.post(
        "/api/collections",
        headers=headers,
        json={
            "hotel_id": str(hotel.id),
            "organic_weight_kg": 10,
            "non_organic_weight_kg": 5,
        },
    )

    logs = (
        await client.get("/api/activity-logs?action=collection.created", headers=headers)
    ).json()
    assert logs["total"] == 1


async def test_alert_acknowledge_is_audited(
    client: AsyncClient, make_hotel: Callable, make_bin: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    bin_ = await make_bin(hotel_id=hotel.id, code="ACT-1")
    headers = await auth_headers(UserRole.ADMIN)
    await client.post(f"/api/bins/{bin_.id}/readings", headers=headers, json={"fill_level": 99})
    alert_id = (await client.get("/api/alerts", headers=headers)).json()["items"][0]["id"]
    await client.post(f"/api/alerts/{alert_id}/acknowledge", headers=headers)

    logs = (
        await client.get("/api/activity-logs?action=alert.acknowledged", headers=headers)
    ).json()
    assert logs["total"] == 1


async def test_activity_logs_forbidden_for_manager(
    client: AsyncClient, auth_headers: Callable
) -> None:
    headers = await auth_headers(UserRole.HOTEL_MANAGER)
    response = await client.get("/api/activity-logs", headers=headers)
    assert response.status_code == 403

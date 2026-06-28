"""Waste collection + AI prediction integration tests (AI client is mocked)."""

from collections.abc import Callable

from httpx import AsyncClient

from app.features.auth.models import UserRole
from app.integrations.ai_service import AIServiceError, get_ai_client
from app.main import app


class FakeAIClient:
    def __init__(self, *, response: dict | None = None, error: Exception | None = None):
        self._response = response
        self._error = error

    async def predict(self, payload: dict) -> dict:
        if self._error is not None:
            raise self._error
        return self._response or {}

    async def health(self) -> bool:
        return True


def _use_ai(fake: FakeAIClient) -> None:
    app.dependency_overrides[get_ai_client] = lambda: fake


async def _create_collection(client, headers, hotel_id, **overrides) -> dict:
    payload = {
        "hotel_id": str(hotel_id),
        "organic_weight_kg": 80,
        "non_organic_weight_kg": 20,
        **overrides,
    }
    response = await client.post("/api/collections", headers=headers, json=payload)
    return response


# ------------------------------- CRUD + RBAC ------------------------------- #


async def test_create_collection_computes_totals(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    headers = await auth_headers(UserRole.OPERATOR)

    response = await _create_collection(client, headers, hotel.id)

    assert response.status_code == 201
    body = response.json()
    assert body["total_weight_kg"] == 100
    assert body["organic_percentage"] == 80.0


async def test_create_collection_forbidden_for_manager(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    headers = await auth_headers(UserRole.HOTEL_MANAGER)

    response = await _create_collection(client, headers, hotel.id)

    assert response.status_code == 403


async def test_create_collection_invalid_hotel(client: AsyncClient, auth_headers: Callable) -> None:
    headers = await auth_headers(UserRole.ADMIN)

    response = await _create_collection(client, headers, "00000000-0000-0000-0000-000000000000")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_create_collection_bin_not_in_hotel(
    client: AsyncClient,
    make_hotel: Callable,
    make_bin: Callable,
    auth_headers: Callable,
) -> None:
    hotel_a = await make_hotel(name="A")
    hotel_b = await make_hotel(name="B")
    bin_b = await make_bin(hotel_id=hotel_b.id, code="B-1")
    headers = await auth_headers(UserRole.ADMIN)

    response = await _create_collection(client, headers, hotel_a.id, bin_id=str(bin_b.id))

    assert response.status_code == 422


async def test_manager_only_sees_own_collections(
    client: AsyncClient,
    make_user: Callable,
    make_hotel: Callable,
    auth_headers: Callable,
    login: Callable,
) -> None:
    manager = await make_user(email="owner@test.io", role=UserRole.HOTEL_MANAGER)
    mine = await make_hotel(name="Mine", manager_id=manager.id)
    theirs = await make_hotel(name="Theirs")
    admin = await auth_headers(UserRole.ADMIN)
    await _create_collection(client, admin, mine.id)
    await _create_collection(client, admin, theirs.id)

    manager_headers = await login("owner@test.io")
    response = await client.get("/api/collections", headers=manager_headers)

    assert response.status_code == 200
    assert response.json()["total"] == 1


async def test_delete_collection_admin_only(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    admin = await auth_headers(UserRole.ADMIN)
    collection_id = (await _create_collection(client, admin, hotel.id)).json()["id"]

    operator = await auth_headers(UserRole.OPERATOR)
    forbidden = await client.delete(f"/api/collections/{collection_id}", headers=operator)
    assert forbidden.status_code == 403

    ok = await client.delete(f"/api/collections/{collection_id}", headers=admin)
    assert ok.status_code == 204


# ----------------------------- AI predictions ----------------------------- #


async def test_predict_success_persists_result(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    headers = await auth_headers(UserRole.OPERATOR)
    collection_id = (await _create_collection(client, headers, hotel.id)).json()["id"]

    _use_ai(
        FakeAIClient(
            response={
                "predicted_energy_kwh": 120.5,
                "predicted_biogas_m3": 30.2,
                "co2_saved_kg": 45.0,
                "model_version": "v1.2",
            }
        )
    )

    response = await client.post(f"/api/collections/{collection_id}/predictions", headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["predicted_energy_kwh"] == 120.5
    assert body["model_version"] == "v1.2"

    latest = await client.get(
        f"/api/collections/{collection_id}/predictions/latest", headers=headers
    )
    assert latest.status_code == 200
    assert latest.json()["co2_saved_kg"] == 45.0


async def test_predict_accepts_aliased_fields(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    headers = await auth_headers(UserRole.OPERATOR)
    collection_id = (await _create_collection(client, headers, hotel.id)).json()["id"]

    # AI returns short field names — the client must still parse them.
    _use_ai(FakeAIClient(response={"energy": 10, "biogas": 5, "co2": 2}))

    response = await client.post(f"/api/collections/{collection_id}/predictions", headers=headers)

    assert response.status_code == 201
    assert response.json()["predicted_energy_kwh"] == 10


async def test_predict_ai_failure_returns_502_and_audits(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    headers = await auth_headers(UserRole.OPERATOR)
    collection_id = (await _create_collection(client, headers, hotel.id)).json()["id"]

    _use_ai(FakeAIClient(error=AIServiceError("AI is down")))

    response = await client.post(f"/api/collections/{collection_id}/predictions", headers=headers)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ai_service_error"

    # The failed attempt is recorded for auditing.
    history = await client.get(f"/api/collections/{collection_id}/predictions", headers=headers)
    body = history.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "failed"
    assert body["items"][0]["error_message"] == "AI is down"


async def test_predict_malformed_response_returns_502(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    headers = await auth_headers(UserRole.OPERATOR)
    collection_id = (await _create_collection(client, headers, hotel.id)).json()["id"]

    _use_ai(FakeAIClient(response={"unexpected": "shape"}))

    response = await client.post(f"/api/collections/{collection_id}/predictions", headers=headers)

    assert response.status_code == 502


async def test_latest_prediction_404_when_none(
    client: AsyncClient, make_hotel: Callable, auth_headers: Callable
) -> None:
    hotel = await make_hotel()
    headers = await auth_headers(UserRole.ADMIN)
    collection_id = (await _create_collection(client, headers, hotel.id)).json()["id"]

    response = await client.get(
        f"/api/collections/{collection_id}/predictions/latest", headers=headers
    )

    assert response.status_code == 404

"""Health endpoint integration test."""

from httpx import AsyncClient


async def test_health_check_ok(client: AsyncClient) -> None:
    response = await client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["service"] == "BioCycle Djerba"

"""Reports tests: summary aggregation, CSV export, scoping, filters."""

import csv
import io
from collections.abc import Callable

from httpx import AsyncClient

from app.features.auth.models import UserRole


async def _hotel_manager(make_user, make_hotel, login, *, email="rep-mgr@test.io"):
    mgr = await make_user(email=email, role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Report Hotel", manager_id=mgr.id, latitude=33.8, longitude=10.8)
    headers = await login(email)
    return mgr, headers


async def _seed_requests(client, headers, op, weights_and_decisions):
    """Create requests and optionally decide them. Returns request ids."""
    ids = []
    for kg, decision in weights_and_decisions:
        rid = (
            await client.post("/api/requests", headers=headers, json={"declared_containers": kg})
        ).json()["id"]
        ids.append(rid)
        if decision == "accept":
            await client.post(f"/api/requests/{rid}/decision", headers=op, json={"accept": True})
        elif decision == "reject":
            await client.post(
                f"/api/requests/{rid}/decision", headers=op,
                json={"accept": False, "rejection_reason": "no"},
            )
    return ids


async def test_summary_totals_and_acceptance(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    _, headers = await _hotel_manager(make_user, make_hotel, login)
    op = await auth_headers(UserRole.OPERATOR)
    await _seed_requests(client, headers, op, [(100, "accept"), (200, "reject"), (300, None)])

    resp = await client.get("/api/reports/summary", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["totals"]["requests"] == 3
    assert body["totals"]["declared_weight_kg"] == 600 * 700
    assert body["totals"]["estimated_methane_m3"] > 0
    assert body["status_counts"]["accepted"] == 1
    assert body["status_counts"]["rejected"] == 1
    assert body["status_counts"]["pending"] == 1
    # 1 accepted of 2 decided -> 50%.
    assert body["acceptance_rate"] == 50.0
    assert body["avg_quality_score"] is not None
    assert body["top_hotels"][0]["hotel_name"] == "Report Hotel"


async def test_csv_export_has_header_and_rows(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    _, headers = await _hotel_manager(make_user, make_hotel, login)
    op = await auth_headers(UserRole.OPERATOR)
    await _seed_requests(client, headers, op, [(100, "accept"), (250, None)])

    resp = await client.get("/api/reports/requests.csv", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]

    reader = list(csv.reader(io.StringIO(resp.text)))
    assert reader[0][0] == "request_id"  # header
    assert reader[0][1] == "hotel_name"
    assert len(reader) == 1 + 2  # header + 2 requests
    # Rows carry the hotel name and a status.
    assert all(row[1] == "Report Hotel" for row in reader[1:])


async def test_reports_scoped_to_manager(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    _, h1 = await _hotel_manager(make_user, make_hotel, login, email="m1@test.io")
    op = await auth_headers(UserRole.OPERATOR)
    await _seed_requests(client, h1, op, [(100, None), (200, None)])

    # Second manager with no requests sees an empty report, not the first's.
    m2 = await make_user(email="m2@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Empty", manager_id=m2.id)
    h2 = await login("m2@test.io")

    summary = (await client.get("/api/reports/summary", headers=h2)).json()
    assert summary["totals"]["requests"] == 0

    csv_rows = list(csv.reader(io.StringIO(
        (await client.get("/api/reports/requests.csv", headers=h2)).text
    )))
    assert len(csv_rows) == 1  # header only


async def test_operator_sees_all_hotels(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    _, h1 = await _hotel_manager(make_user, make_hotel, login, email="a@test.io")
    op_headers_creator = await auth_headers(UserRole.OPERATOR, email="op1@test.io")
    await _seed_requests(client, h1, op_headers_creator, [(100, None)])

    m2 = await make_user(email="b@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Hotel B", manager_id=m2.id)
    h2 = await login("b@test.io")
    await _seed_requests(client, h2, op_headers_creator, [(200, None)])

    # An operator's report spans both hotels.
    op = await auth_headers(UserRole.OPERATOR, email="op2@test.io")
    summary = (await client.get("/api/reports/summary", headers=op)).json()
    assert summary["totals"]["requests"] == 2


async def test_status_filter(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    _, headers = await _hotel_manager(make_user, make_hotel, login)
    op = await auth_headers(UserRole.OPERATOR)
    await _seed_requests(client, headers, op, [(100, "accept"), (200, "reject"), (300, None)])

    resp = await client.get("/api/reports/summary?status=rejected", headers=headers)
    body = resp.json()
    assert body["totals"]["requests"] == 1
    assert body["status_counts"]["rejected"] == 1


async def test_reports_require_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/reports/summary")).status_code == 401
    assert (await client.get("/api/reports/requests.csv")).status_code == 401

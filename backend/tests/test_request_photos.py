"""Photo upload/download/delete integration tests.

Exercises the full multipart path against a temp upload dir: validation (MIME,
size, quota), ownership + lifecycle rules, JWT-gated download (no public URL),
and deletion. Files are written to a pytest tmp dir via a settings override.
"""

from collections.abc import Callable

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.features.auth.models import UserRole

# Minimal valid-enough file bodies (content-type is what the service checks).
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 64


@pytest.fixture(autouse=True)
def _tmp_upload_dir(tmp_path, monkeypatch):
    """Point storage at a throwaway dir for every test in this module."""
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))


async def _hotel_manager(make_user, make_hotel, login, *, email="ph-mgr@test.io"):
    manager = await make_user(email=email, role=UserRole.HOTEL_MANAGER)
    hotel = await make_hotel(name="Photo Hotel", manager_id=manager.id)
    headers = await login(email)
    return headers, hotel


async def _create_request(client, headers, kg=100) -> str:
    resp = await client.post("/api/requests", headers=headers, json={"declared_weight_kg": kg})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _file(name: str, body: bytes, content_type: str):
    return ("files", (name, body, content_type))


# --------------------------------------------------------------------------- #
# Upload
# --------------------------------------------------------------------------- #
async def test_upload_photos_success(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    rid = await _create_request(client, headers)

    resp = await client.post(
        f"/api/requests/{rid}/photos",
        headers=headers,
        files=[_file("a.png", PNG_BYTES, "image/png"), _file("b.jpg", JPEG_BYTES, "image/jpeg")],
    )

    assert resp.status_code == 201, resp.text
    photos = resp.json()
    assert len(photos) == 2
    assert all(p["size_bytes"] > 0 for p in photos)

    # They show up on the request detail.
    detail = await client.get(f"/api/requests/{rid}", headers=headers)
    assert len(detail.json()["photos"]) == 2


async def test_upload_rejects_bad_mime(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    rid = await _create_request(client, headers)

    resp = await client.post(
        f"/api/requests/{rid}/photos",
        headers=headers,
        files=[_file("doc.pdf", b"%PDF-1.4", "application/pdf")],
    )
    assert resp.status_code == 422


async def test_upload_rejects_oversize(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    monkeypatch,
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    rid = await _create_request(client, headers)

    # Shrink the cap so we don't have to ship 10 MB in the test.
    monkeypatch.setattr(settings, "MAX_PHOTO_SIZE_MB", 0.001)  # ~1 KB
    big = b"\x89PNG\r\n\x1a\n" + b"\x00" * 5000

    resp = await client.post(
        f"/api/requests/{rid}/photos",
        headers=headers,
        files=[_file("big.png", big, "image/png")],
    )
    assert resp.status_code == 422
    assert "MB" in resp.json()["error"]["message"]


async def test_upload_enforces_quota(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    monkeypatch,
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    rid = await _create_request(client, headers)

    monkeypatch.setattr(settings, "MAX_PHOTOS_PER_REQUEST", 2)
    files = [_file(f"{i}.png", PNG_BYTES, "image/png") for i in range(3)]

    resp = await client.post(f"/api/requests/{rid}/photos", headers=headers, files=files)
    assert resp.status_code == 409
    assert "at most 2" in resp.json()["error"]["message"]


async def test_operator_cannot_upload(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    rid = await _create_request(client, headers)

    op = await auth_headers(UserRole.OPERATOR)
    resp = await client.post(
        f"/api/requests/{rid}/photos", headers=op,
        files=[_file("a.png", PNG_BYTES, "image/png")],
    )
    assert resp.status_code == 403


# --------------------------------------------------------------------------- #
# Download (JWT-gated, not public)
# --------------------------------------------------------------------------- #
async def test_download_requires_auth(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    rid = await _create_request(client, headers)
    up = await client.post(
        f"/api/requests/{rid}/photos", headers=headers,
        files=[_file("a.png", PNG_BYTES, "image/png")],
    )
    pid = up.json()[0]["id"]

    # No Authorization header -> 401. A direct URL is useless without a token.
    resp = await client.get(f"/api/requests/{rid}/photos/{pid}")
    assert resp.status_code == 401


async def test_download_success_and_operator_access(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    rid = await _create_request(client, headers)
    up = await client.post(
        f"/api/requests/{rid}/photos", headers=headers,
        files=[_file("a.png", PNG_BYTES, "image/png")],
    )
    pid = up.json()[0]["id"]

    # Owner can fetch the bytes.
    owner_resp = await client.get(f"/api/requests/{rid}/photos/{pid}", headers=headers)
    assert owner_resp.status_code == 200
    assert owner_resp.headers["content-type"] == "image/png"
    assert owner_resp.content == PNG_BYTES

    # An operator (allowed to see any request) can too.
    op = await auth_headers(UserRole.OPERATOR)
    op_resp = await client.get(f"/api/requests/{rid}/photos/{pid}", headers=op)
    assert op_resp.status_code == 200


async def test_other_hotel_cannot_download(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    h1, _ = await _hotel_manager(make_user, make_hotel, login, email="h1@test.io")
    rid = await _create_request(client, h1)
    up = await client.post(
        f"/api/requests/{rid}/photos", headers=h1,
        files=[_file("a.png", PNG_BYTES, "image/png")],
    )
    pid = up.json()[0]["id"]

    m2 = await make_user(email="h2@test.io", role=UserRole.HOTEL_MANAGER)
    await make_hotel(name="Other", manager_id=m2.id)
    h2 = await login("h2@test.io")

    # 404 (not 403): don't leak existence.
    resp = await client.get(f"/api/requests/{rid}/photos/{pid}", headers=h2)
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Delete + lifecycle
# --------------------------------------------------------------------------- #
async def test_delete_photo(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    rid = await _create_request(client, headers)
    up = await client.post(
        f"/api/requests/{rid}/photos", headers=headers,
        files=[_file("a.png", PNG_BYTES, "image/png")],
    )
    pid = up.json()[0]["id"]

    resp = await client.delete(f"/api/requests/{rid}/photos/{pid}", headers=headers)
    assert resp.status_code == 204

    detail = await client.get(f"/api/requests/{rid}", headers=headers)
    assert detail.json()["photos"] == []


async def test_cannot_upload_to_terminal_request(
    client: AsyncClient, make_user: Callable, make_hotel: Callable, login: Callable,
    auth_headers: Callable,
) -> None:
    headers, _ = await _hotel_manager(make_user, make_hotel, login)
    rid = await _create_request(client, headers)

    # Operator rejects it -> terminal state.
    op = await auth_headers(UserRole.OPERATOR)
    await client.post(
        f"/api/requests/{rid}/decision", headers=op,
        json={"accept": False, "rejection_reason": "no"},
    )

    resp = await client.post(
        f"/api/requests/{rid}/photos", headers=headers,
        files=[_file("a.png", PNG_BYTES, "image/png")],
    )
    assert resp.status_code == 409

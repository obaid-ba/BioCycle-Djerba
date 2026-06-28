"""Realtime + MQTT tests — broker-free.

Covers the WebSocket auth gate, the ConnectionManager fan-out, the pure event
builder, and the MQTT parsing helpers. The broker->loop bridge is integration-
only and intentionally not unit-tested here.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token
from app.features.bins.models import BinStatus, SensorReading, SmartBin
from app.features.bins.schemas import SensorReadingCreate
from app.features.bins.service import BinService
from app.main import app
from app.mqtt.processor import extract_bin_code, normalize_payload
from app.realtime.events import build_reading_event
from app.realtime.manager import ConnectionManager

# --------------------------- ConnectionManager ----------------------------- #


class _FakeWebSocket:
    def __init__(self, *, fail: bool = False) -> None:
        self.accepted = False
        self.sent: list[dict] = []
        self._fail = fail

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict) -> None:
        if self._fail:
            raise RuntimeError("socket closed")
        self.sent.append(data)


async def test_manager_broadcasts_to_connections() -> None:
    manager = ConnectionManager()
    a, b = _FakeWebSocket(), _FakeWebSocket()
    await manager.connect(a)
    await manager.connect(b)

    await manager.broadcast({"hello": "world"})

    assert a.accepted and b.accepted
    assert a.sent == [{"hello": "world"}]
    assert b.sent == [{"hello": "world"}]
    assert manager.count == 2


async def test_manager_drops_dead_connections() -> None:
    manager = ConnectionManager()
    good, dead = _FakeWebSocket(), _FakeWebSocket(fail=True)
    await manager.connect(good)
    await manager.connect(dead)

    await manager.broadcast({"x": 1})

    assert manager.count == 1
    assert good.sent == [{"x": 1}]


# ------------------------------ event builder ------------------------------ #


def test_build_reading_event() -> None:
    bin_ = SmartBin(
        id=uuid.uuid4(),
        code="ESP32-9",
        hotel_id=uuid.uuid4(),
        status=BinStatus.ONLINE,
        fill_level=42.0,
        battery_level=80.0,
    )
    reading = SensorReading(
        id=uuid.uuid4(),
        bin_id=bin_.id,
        fill_level=42.0,
        temperature_c=25.0,
        recorded_at=datetime(2026, 6, 28, 12, 0, tzinfo=UTC),
    )

    event = build_reading_event(bin_, reading)

    assert event["type"] == "bin.reading"
    assert event["data"]["code"] == "ESP32-9"
    assert event["data"]["status"] == "online"
    assert event["data"]["fill_level"] == 42.0
    assert event["data"]["temperature_c"] == 25.0
    assert event["data"]["recorded_at"].startswith("2026-06-28T12:00:00")


# --------------------------- MQTT pure helpers ----------------------------- #


def test_extract_bin_code() -> None:
    assert extract_bin_code("biocycle/ESP32-1/telemetry") == "ESP32-1"
    assert extract_bin_code("biocycle/ESP32-1/status") is None
    assert extract_bin_code("garbage") is None


def test_normalize_payload_maps_aliases() -> None:
    raw = {"fill": 60, "temp": 30, "battery": 90, "humidity": 55, "unknown": 1}
    assert normalize_payload(raw) == {
        "fill_level": 60,
        "temperature_c": 30,
        "battery_level": 90,
        "humidity": 55,
    }


# ----------------------- service ingest returns event ---------------------- #


async def test_service_ingest_returns_event(
    db_session, make_hotel: Callable, make_bin: Callable
) -> None:
    hotel = await make_hotel()
    bin_ = await make_bin(hotel_id=hotel.id, code="EVT-1")

    reading, event = await BinService(db_session).ingest(
        bin_id=bin_.id,
        data=SensorReadingCreate(fill_level=33.0, battery_level=77.0),
    )

    assert reading.fill_level == 33.0
    assert event["type"] == "bin.reading"
    assert event["data"]["code"] == "EVT-1"
    assert event["data"]["status"] == "online"


async def test_service_ingest_by_unknown_code_raises(db_session) -> None:
    from app.shared.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await BinService(db_session).ingest(
            code="does-not-exist", data=SensorReadingCreate(fill_level=10.0)
        )


# ------------------------------ WebSocket auth ----------------------------- #


def test_ws_rejected_without_token() -> None:
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/ws") as ws:
            ws.receive_text()


def test_ws_accepts_with_valid_token() -> None:
    token = create_access_token(str(uuid.uuid4()), "admin")
    client = TestClient(app)
    with client.websocket_connect(f"/api/ws?token={token}") as ws:
        message = ws.receive_json()
        assert message == {"type": "connection.ack"}

"""Firebase integration tests: detection aggregation + reader (mocked HTTP).

No live Firebase connection — the reader is tested against a mocked RTDB
response shaped like the real /AI_System node.
"""

import uuid

import httpx
import pytest

from app.integrations.firebase.aggregator import aggregate_detections
from app.integrations.firebase.reader import FirebaseError, FirebaseRealtimeReader

# A slice of the real /AI_System node: 7 organic + 3 recyclable detections.
SAMPLE_NODE = {
    "camera": "online",
    "fps": 30,
    "resolution": "640x480",
    "objects_detected": 0,
    "detections": {
        "-a1": {"prediction": "O", "confidence": 0.68},
        "-a2": {"prediction": "O", "confidence": 0.77},
        "-a3": {"prediction": "O", "confidence": 0.71},
        "-a4": {"prediction": "O", "confidence": 0.74},
        "-a5": {"prediction": "O", "confidence": 0.80},
        "-a6": {"prediction": "O", "confidence": 0.66},
        "-a7": {"prediction": "O", "confidence": 0.67},
        "-b1": {"prediction": "R", "confidence": 0.85},
        "-b2": {"prediction": "R", "confidence": 0.84},
        "-b3": {"prediction": "R", "confidence": 0.88},
    },
}


# --------------------------------------------------------------------------- #
# Aggregator (pure logic)
# --------------------------------------------------------------------------- #
def test_aggregate_purity_and_contamination() -> None:
    r = aggregate_detections(SAMPLE_NODE["detections"], declared_weight_kg=2100)
    assert r.organic_purity == 70.0  # 7 / 10
    assert r.contamination == 30.0
    assert 0 < r.confidence <= 1
    assert r.estimated_methane_m3 > 0
    assert r.model_version.startswith("firebase")


def test_aggregate_all_organic() -> None:
    detections = {"x": {"prediction": "O", "confidence": 0.9}}
    r = aggregate_detections(detections, declared_weight_kg=700)
    assert r.organic_purity == 100.0
    assert r.contamination == 0.0


def test_aggregate_empty_is_neutral_not_error() -> None:
    r = aggregate_detections({}, declared_weight_kg=700)
    assert r.organic_purity == 0.0
    assert r.quality_score == 0.0
    assert r.confidence == 0.0


def test_aggregate_ignores_malformed_entries() -> None:
    detections = {
        "ok": {"prediction": "O", "confidence": 0.8},
        "bad1": "not a dict",
        "bad2": {"prediction": "X", "confidence": 0.9},  # unknown label
        "bad3": {"confidence": 0.5},  # no label
    }
    r = aggregate_detections(detections, declared_weight_kg=700)
    # Only the one valid organic detection counts -> 100% purity.
    assert r.organic_purity == 100.0


# --------------------------------------------------------------------------- #
# Reader (mocked HTTP; verifies read-only + aggregation wiring)
# --------------------------------------------------------------------------- #
async def test_reader_aggregates_from_node(monkeypatch) -> None:
    async def fake_get(self, url, params=None):  # noqa: ANN001
        assert url.endswith("/AI_System.json")  # reads the configured node
        return httpx.Response(200, json=SAMPLE_NODE)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    reader = FirebaseRealtimeReader(
        db_url="https://example-rtdb.firebasedatabase.app",
        credentials_path="",  # unauthenticated path
        node="AI_System",
    )
    result = await reader.get_analysis(request_id=uuid.uuid4(), declared_weight_kg=2100)
    assert result.organic_purity == 70.0
    assert result.estimated_methane_m3 > 0


async def test_reader_raises_on_http_error(monkeypatch) -> None:
    async def fake_get(self, url, params=None):  # noqa: ANN001
        return httpx.Response(403, text="Permission denied")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    reader = FirebaseRealtimeReader(
        db_url="https://example-rtdb.firebasedatabase.app", credentials_path=""
    )
    with pytest.raises(FirebaseError):
        await reader.get_analysis(request_id=uuid.uuid4(), declared_weight_kg=700)


def test_reader_is_read_only() -> None:
    """The reader must expose no write/delete/update methods — read-only contract."""
    reader = FirebaseRealtimeReader(db_url="https://x.firebasedatabase.app")
    public = {m for m in dir(reader) if not m.startswith("_")}
    forbidden = {"write", "set", "update", "delete", "push", "put", "post"}
    assert public & forbidden == set(), f"reader exposes write methods: {public & forbidden}"


# --------------------------------------------------------------------------- #
# Live summary (dashboard)
# --------------------------------------------------------------------------- #
def test_summarize_live() -> None:
    from app.integrations.firebase.aggregator import summarize_live

    s = summarize_live(SAMPLE_NODE)
    assert s["camera"] == "online"
    assert s["organic_count"] == 7
    assert s["recyclable_count"] == 3
    assert s["total_detections"] == 10
    assert s["organic_purity"] == 70.0
    assert 0 < s["avg_confidence"] <= 1


def test_summarize_live_empty() -> None:
    from app.integrations.firebase.aggregator import summarize_live

    s = summarize_live({})
    assert s["total_detections"] == 0
    assert s["organic_purity"] is None

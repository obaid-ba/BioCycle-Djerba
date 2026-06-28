"""MQTT message processing pipeline.

Pure helpers (`extract_bin_code`, `normalize_payload`) are unit-tested in
isolation; `process_message` wires them to the database + broadcast and is
exercised end-to-end via the broker in a running system.
"""

import json

from pydantic import ValidationError as PydanticValidationError

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.features.bins.schemas import SensorReadingCreate
from app.features.bins.service import BinService
from app.realtime.manager import manager
from app.shared.exceptions import NotFoundError

logger = get_logger(__name__)

# Map a variety of likely device field names onto our schema fields.
PAYLOAD_ALIASES = {
    "fill": "fill_level",
    "fill_level": "fill_level",
    "level": "fill_level",
    "weight": "weight_kg",
    "weight_kg": "weight_kg",
    "temperature": "temperature_c",
    "temp": "temperature_c",
    "temperature_c": "temperature_c",
    "humidity": "humidity",
    "hum": "humidity",
    "battery": "battery_level",
    "battery_level": "battery_level",
    "recorded_at": "recorded_at",
    "timestamp": "recorded_at",
}


def extract_bin_code(topic: str) -> str | None:
    """Parse `biocycle/{code}/telemetry` -> code."""
    parts = topic.split("/")
    if len(parts) >= 3 and parts[0] == "biocycle" and parts[-1] == "telemetry":
        return parts[1]
    return None


def normalize_payload(raw: dict) -> dict:
    """Project a raw device dict onto known schema fields via the alias map."""
    normalized: dict = {}
    for key, value in raw.items():
        mapped = PAYLOAD_ALIASES.get(str(key).lower())
        if mapped is not None:
            normalized[mapped] = value
    return normalized


async def process_message(topic: str, payload: bytes | str) -> bool:
    """Parse, persist, and broadcast a single telemetry message.

    Returns True if a reading was ingested. Never raises — a single bad message
    must not take down the consumer.
    """
    code = extract_bin_code(topic)
    if code is None:
        logger.warning("Ignoring message on unrecognized topic: %s", topic)
        return False

    try:
        raw = json.loads(payload)
    except (ValueError, TypeError):
        logger.warning("Invalid JSON payload on topic %s", topic)
        return False
    if not isinstance(raw, dict):
        logger.warning("Expected JSON object on topic %s", topic)
        return False

    try:
        reading_in = SensorReadingCreate(**normalize_payload(raw))
    except PydanticValidationError as exc:
        logger.warning("Invalid telemetry for bin %s: %s", code, exc)
        return False

    async with AsyncSessionLocal() as db:
        try:
            _, event = await BinService(db).ingest(code=code, data=reading_in)
        except NotFoundError:
            logger.warning("Telemetry for unknown bin code: %s", code)
            return False

    await manager.broadcast(event)
    return True

"""Realtime event builders.

Pure functions that translate domain objects into the JSON envelope broadcast
over WebSockets. Kept dependency-free (no manager, no DB) so they're trivially
unit-testable and reusable by any edge that needs to publish.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.features.bins.models import SensorReading, SmartBin

EVENT_BIN_READING = "bin.reading"


def build_reading_event(bin_: "SmartBin", reading: "SensorReading") -> dict:
    """Envelope for a new sensor reading, including the bin's refreshed state."""
    return {
        "type": EVENT_BIN_READING,
        "data": {
            "bin_id": str(bin_.id),
            "code": bin_.code,
            "hotel_id": str(bin_.hotel_id),
            "status": bin_.status.value,
            "fill_level": reading.fill_level,
            "battery_level": reading.battery_level,
            "temperature_c": reading.temperature_c,
            "humidity": reading.humidity,
            "weight_kg": reading.weight_kg,
            "recorded_at": reading.recorded_at.isoformat() if reading.recorded_at else None,
        },
    }

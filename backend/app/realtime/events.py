"""Realtime event builders.

Pure functions that translate domain objects into the JSON envelope broadcast
over WebSockets. Kept dependency-free (no manager, no DB) so they're trivially
unit-testable and reusable by any edge that needs to publish.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.features.alerts.models import Alert
    from app.features.bins.models import SensorReading, SmartBin

EVENT_BIN_READING = "bin.reading"
EVENT_ALERT = "alert"


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


def build_alert_event(alert: "Alert") -> dict:
    """Envelope for an alert (creation or status change)."""
    return {
        "type": EVENT_ALERT,
        "data": {
            "id": str(alert.id),
            "hotel_id": str(alert.hotel_id) if alert.hotel_id else None,
            "bin_id": str(alert.bin_id) if alert.bin_id else None,
            "alert_type": alert.type.value,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "title": alert.title,
            "message": alert.message,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
        },
    }

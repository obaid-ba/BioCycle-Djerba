"""Smart bin and sensor reading models.

`SmartBin` caches its latest telemetry (fill/battery/status/last_reading_at) so
dashboards can read current state cheaply; `SensorReading` is the append-only
time-series of raw device messages.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import Base, TimestampMixin, UUIDMixin


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class BinType(str, enum.Enum):
    ORGANIC = "organic"
    NON_ORGANIC = "non_organic"
    MIXED = "mixed"


class BinStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class SmartBin(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "smart_bins"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    hotel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hotels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bin_type: Mapped[BinType] = mapped_column(
        Enum(BinType, name="bin_type", values_callable=_enum_values),
        default=BinType.MIXED,
        server_default=BinType.MIXED.value,
        nullable=False,
    )
    status: Mapped[BinStatus] = mapped_column(
        Enum(BinStatus, name="bin_status", values_callable=_enum_values),
        default=BinStatus.OFFLINE,
        server_default=BinStatus.OFFLINE.value,
        nullable=False,
        index=True,
    )
    capacity_liters: Mapped[float | None] = mapped_column(Float)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    # Denormalized latest telemetry (updated on each ingested reading).
    fill_level: Mapped[float | None] = mapped_column(Float)
    battery_level: Mapped[float | None] = mapped_column(Float)
    last_reading_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SmartBin {self.code}>"


class SensorReading(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "sensor_readings"
    __table_args__ = (Index("ix_sensor_readings_bin_recorded", "bin_id", "recorded_at"),)

    bin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("smart_bins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fill_level: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    temperature_c: Mapped[float | None] = mapped_column(Float)
    humidity: Mapped[float | None] = mapped_column(Float)
    battery_level: Mapped[float | None] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SensorReading bin={self.bin_id} fill={self.fill_level}>"

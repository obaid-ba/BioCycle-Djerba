"""Alert model and enumerations."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import Base, TimestampMixin, UUIDMixin


def _vals(enum_cls: type[enum.Enum]) -> list[str]:
    return [m.value for m in enum_cls]


class AlertType(str, enum.Enum):
    BIN_FULL = "bin_full"
    BIN_BATTERY_LOW = "bin_battery_low"
    BIN_OFFLINE = "bin_offline"
    SYSTEM = "system"
    CUSTOM = "custom"


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class Alert(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "alerts"

    hotel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hotels.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    bin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("smart_bins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type: Mapped[AlertType] = mapped_column(
        Enum(AlertType, name="alert_type", values_callable=_vals),
        nullable=False,
        index=True,
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity", values_callable=_vals),
        nullable=False,
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status", values_callable=_vals),
        default=AlertStatus.OPEN,
        server_default=AlertStatus.OPEN.value,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    context: Mapped[dict | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))

    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Alert {self.type.value} {self.status.value}>"

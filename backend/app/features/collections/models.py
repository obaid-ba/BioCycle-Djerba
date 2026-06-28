"""Waste collection and AI prediction models."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import Base, TimestampMixin, UUIDMixin


class PredictionStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"


class WasteCollection(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "waste_collections"

    hotel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hotels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("smart_bins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    organic_weight_kg: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0", nullable=False
    )
    non_organic_weight_kg: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0", nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WasteCollection {self.id} hotel={self.hotel_id}>"


class Prediction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "predictions"

    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("waste_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[PredictionStatus] = mapped_column(
        Enum(
            PredictionStatus,
            name="prediction_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    predicted_energy_kwh: Mapped[float | None] = mapped_column(Float)
    predicted_biogas_m3: Mapped[float | None] = mapped_column(Float)
    co2_saved_kg: Mapped[float | None] = mapped_column(Float)
    model_version: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    raw_response: Mapped[dict | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Prediction {self.id} status={self.status.value}>"

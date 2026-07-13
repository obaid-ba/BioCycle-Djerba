"""Collection request models.

`CollectionRequest` is the product's central aggregate: a hotel's declared
organic-waste pickup, enriched by external-AI scores, triaged and driven through
its lifecycle by an operator. `RequestPhoto` holds the (0..n) photos attached to
a request; binary upload is a later brick — this iteration models the relation
and metadata only.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.features.requests.state_machine import RequestStatus
from app.shared.models import Base, TimestampMixin, UUIDMixin


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class AIStatus(str, enum.Enum):
    """Progress of the external-AI analysis for a request."""

    PENDING = "pending"   # not yet scored
    SUCCESS = "success"   # scores populated
    FAILED = "failed"     # scoring errored (see ai_error); re-triable


class CollectionRequest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "collection_requests"

    hotel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hotels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, name="request_status", values_callable=_enum_values),
        default=RequestStatus.PENDING,
        server_default=RequestStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    # ---- Declared / measured quantities ----
    declared_weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    # Captured by the operator at the COLLECTED step (real weight on the truck).
    collected_weight_kg: Mapped[float | None] = mapped_column(Float)

    # Straight-line distance hotel -> plant, snapshotted at creation from the
    # hotel's coordinates. Drives the operator-queue tiebreak (closest first) and
    # is shown to the operator so the ordering is explainable. NULL when the
    # hotel has no coordinates.
    distance_to_plant_km: Mapped[float | None] = mapped_column(Float, index=True)

    # ---- External-AI results (all nullable; filled asynchronously) ----
    ai_status: Mapped[AIStatus] = mapped_column(
        Enum(AIStatus, name="ai_status", values_callable=_enum_values),
        default=AIStatus.PENDING,
        server_default=AIStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    ai_quality_score: Mapped[float | None] = mapped_column(Float)        # 0..100
    ai_organic_purity: Mapped[float | None] = mapped_column(Float)       # %
    ai_contamination: Mapped[float | None] = mapped_column(Float)        # %
    ai_estimated_methane_m3: Mapped[float | None] = mapped_column(Float)
    ai_estimated_energy_kwh: Mapped[float | None] = mapped_column(Float)
    ai_estimated_co2_kg: Mapped[float | None] = mapped_column(Float)
    # The queue's sort key. Indexed because the operator dashboard orders by it.
    ai_priority_score: Mapped[float | None] = mapped_column(Float, index=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float)           # 0..1
    ai_model_version: Mapped[str | None] = mapped_column(String(64))
    ai_error: Mapped[str | None] = mapped_column(String(500))

    # ---- Operator decision & lifecycle tracking ----
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    operator_notes: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    photos: Mapped[list["RequestPhoto"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CollectionRequest {self.id} {self.status.value} {self.declared_weight_kg}kg>"


class RequestPhoto(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "request_photos"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collection_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int | None] = mapped_column(Integer)

    request: Mapped["CollectionRequest"] = relationship(back_populates="photos")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RequestPhoto {self.id} req={self.request_id}>"

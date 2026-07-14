"""Collection-request DTOs — the public request/response contracts.

These are the only shapes the HTTP layer speaks; ORM models never cross the API
boundary directly (except via `from_attributes` serialization on the read path).
"""

import uuid
from datetime import datetime

from pydantic import Field

from app.features.requests.models import AIStatus
from app.features.requests.state_machine import RequestStatus
from app.shared.schemas import BaseSchema


# --------------------------------------------------------------------------- #
# Create (Hotel)
# --------------------------------------------------------------------------- #
class CollectionRequestCreate(BaseSchema):
    """Payload a hotel submits to open a new collection request."""

    declared_containers: int = Field(
        gt=0,
        le=1000,
        description=(
            "Number of standard containers of organic waste declared by the "
            "hotel. The weight in kg is derived server-side "
            "(containers × CONTAINER_WEIGHT_KG)."
        ),
    )
    # hotel_id is NOT accepted from the body: it is derived server-side from the
    # authenticated hotel manager, so a hotel can never file for another hotel.


# --------------------------------------------------------------------------- #
# Operator decision & lifecycle transitions
# --------------------------------------------------------------------------- #
class RequestDecision(BaseSchema):
    """Operator accept/reject decision on a PENDING/AI_FAILED request."""

    accept: bool = Field(description="True to accept the request, False to reject it.")
    rejection_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Required-in-spirit when rejecting; surfaced to the hotel.",
    )
    notes: str | None = Field(default=None, description="Free-form operator notes.")


class RequestTransition(BaseSchema):
    """Operator-driven lifecycle move after acceptance."""

    target: RequestStatus = Field(
        description="Next lifecycle state (on_the_way | collected | completed).",
    )
    collected_weight_kg: float | None = Field(
        default=None,
        gt=0,
        le=100_000,
        description="Real collected weight; required when target is 'collected'.",
    )
    notes: str | None = Field(default=None, description="Free-form operator notes.")


# --------------------------------------------------------------------------- #
# AI result (written by the integration layer / stub)
# --------------------------------------------------------------------------- #
class AIResult(BaseSchema):
    """Normalized scores returned by the external AI for one request."""

    quality_score: float = Field(ge=0, le=100)
    organic_purity: float = Field(ge=0, le=100)
    contamination: float = Field(ge=0, le=100)
    estimated_methane_m3: float = Field(ge=0)
    estimated_energy_kwh: float = Field(ge=0)
    estimated_co2_kg: float = Field(ge=0)
    priority_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    model_version: str


# --------------------------------------------------------------------------- #
# Read
# --------------------------------------------------------------------------- #
class RequestPhotoRead(BaseSchema):
    id: uuid.UUID
    storage_path: str
    content_type: str | None
    size_bytes: int | None
    created_at: datetime


class CollectionRequestRead(BaseSchema):
    id: uuid.UUID
    hotel_id: uuid.UUID
    status: RequestStatus

    declared_containers: int
    declared_weight_kg: float
    collected_weight_kg: float | None
    distance_to_plant_km: float | None

    ai_status: AIStatus
    ai_quality_score: float | None
    ai_organic_purity: float | None
    ai_contamination: float | None
    ai_estimated_methane_m3: float | None
    ai_estimated_energy_kwh: float | None
    ai_estimated_co2_kg: float | None
    ai_priority_score: float | None
    ai_confidence: float | None
    ai_model_version: str | None
    ai_error: str | None

    decided_by: uuid.UUID | None
    decided_at: datetime | None
    rejection_reason: str | None
    operator_notes: str | None
    completed_at: datetime | None

    photos: list[RequestPhotoRead]

    created_at: datetime
    updated_at: datetime

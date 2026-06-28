"""Waste collection and prediction DTOs."""

import uuid
from datetime import datetime

from pydantic import Field, computed_field

from app.features.collections.models import PredictionStatus
from app.shared.schemas import BaseSchema


class WasteCollectionCreate(BaseSchema):
    hotel_id: uuid.UUID
    bin_id: uuid.UUID | None = None
    collected_at: datetime | None = None
    organic_weight_kg: float = Field(ge=0)
    non_organic_weight_kg: float = Field(ge=0)
    notes: str | None = None


class WasteCollectionUpdate(BaseSchema):
    bin_id: uuid.UUID | None = None
    collected_at: datetime | None = None
    organic_weight_kg: float | None = Field(default=None, ge=0)
    non_organic_weight_kg: float | None = Field(default=None, ge=0)
    notes: str | None = None


class WasteCollectionRead(BaseSchema):
    id: uuid.UUID
    hotel_id: uuid.UUID
    bin_id: uuid.UUID | None
    collected_at: datetime
    organic_weight_kg: float
    non_organic_weight_kg: float
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def total_weight_kg(self) -> float:
        return round(self.organic_weight_kg + self.non_organic_weight_kg, 3)

    @computed_field
    @property
    def organic_percentage(self) -> float | None:
        total = self.organic_weight_kg + self.non_organic_weight_kg
        if total <= 0:
            return None
        return round(self.organic_weight_kg / total * 100, 1)


class PredictionRead(BaseSchema):
    id: uuid.UUID
    collection_id: uuid.UUID
    status: PredictionStatus
    predicted_energy_kwh: float | None
    predicted_biogas_m3: float | None
    co2_saved_kg: float | None
    model_version: str | None
    error_message: str | None
    created_at: datetime

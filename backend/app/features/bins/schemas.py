"""Smart bin and sensor reading DTOs."""

import uuid
from datetime import datetime

from pydantic import Field

from app.features.bins.models import BinStatus, BinType
from app.shared.schemas import BaseSchema


class SmartBinBase(BaseSchema):
    code: str = Field(min_length=1, max_length=64, description="Unique device code")
    name: str | None = Field(default=None, max_length=255)
    bin_type: BinType = BinType.MIXED
    status: BinStatus = BinStatus.OFFLINE
    capacity_liters: float | None = Field(default=None, ge=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class SmartBinCreate(SmartBinBase):
    hotel_id: uuid.UUID


class SmartBinUpdate(BaseSchema):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    hotel_id: uuid.UUID | None = None
    bin_type: BinType | None = None
    status: BinStatus | None = None
    capacity_liters: float | None = Field(default=None, ge=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class SmartBinRead(BaseSchema):
    id: uuid.UUID
    code: str
    name: str | None
    hotel_id: uuid.UUID
    bin_type: BinType
    status: BinStatus
    capacity_liters: float | None
    latitude: float | None
    longitude: float | None
    fill_level: float | None
    battery_level: float | None
    last_reading_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SensorReadingCreate(BaseSchema):
    fill_level: float = Field(ge=0, le=100)
    weight_kg: float | None = Field(default=None, ge=0)
    temperature_c: float | None = Field(default=None, ge=-50, le=150)
    humidity: float | None = Field(default=None, ge=0, le=100)
    battery_level: float | None = Field(default=None, ge=0, le=100)
    recorded_at: datetime | None = Field(
        default=None, description="Device timestamp; defaults to server time"
    )


class SensorReadingRead(BaseSchema):
    id: uuid.UUID
    bin_id: uuid.UUID
    fill_level: float
    weight_kg: float | None
    temperature_c: float | None
    humidity: float | None
    battery_level: float | None
    recorded_at: datetime
    created_at: datetime

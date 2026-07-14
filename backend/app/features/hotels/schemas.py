"""Hotel DTOs."""

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.features.hotels.models import HotelStatus
from app.shared.schemas import BaseSchema


class HotelBase(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    city: str = Field(min_length=1, max_length=120)
    country: str = Field(default="Tunisia", max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=50)
    status: HotelStatus = HotelStatus.ONBOARDING


class HotelCreate(HotelBase):
    manager_id: uuid.UUID | None = None


class HotelUpdate(BaseSchema):
    """All fields optional — only provided fields are applied (PATCH semantics)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=50)
    status: HotelStatus | None = None
    manager_id: uuid.UUID | None = None


class HotelRead(BaseSchema):
    id: uuid.UUID
    name: str
    address: str | None
    city: str
    country: str
    latitude: float | None
    longitude: float | None
    contact_email: EmailStr | None
    contact_phone: str | None
    status: HotelStatus
    manager_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

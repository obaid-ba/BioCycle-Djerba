"""Hotel model and status enumeration."""

import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import Base, TimestampMixin, UUIDMixin


class HotelStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ONBOARDING = "onboarding"


class Hotel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "hotels"

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    address: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    country: Mapped[str] = mapped_column(
        String(120), default="Tunisia", server_default="Tunisia", nullable=False
    )
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    number_of_rooms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[HotelStatus] = mapped_column(
        Enum(
            HotelStatus,
            name="hotel_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=HotelStatus.ONBOARDING,
        server_default=HotelStatus.ONBOARDING.value,
        nullable=False,
        index=True,
    )
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Hotel {self.name} ({self.city})>"

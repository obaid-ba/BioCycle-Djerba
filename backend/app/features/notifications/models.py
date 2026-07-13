"""Notification model and type enumeration."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import Base, TimestampMixin, UUIDMixin


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class NotificationType(str, enum.Enum):
    """What a notification is about. Extensible as new events are wired in."""

    REQUEST_ACCEPTED = "request_accepted"
    REQUEST_REJECTED = "request_rejected"
    REQUEST_COMPLETED = "request_completed"


class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type", values_callable=_enum_values),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(String(500))
    # Link back to the request this is about (nullable so the notification
    # survives if the request is ever deleted).
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collection_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False, index=True
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Notification {self.id} {self.type.value} user={self.user_id}>"

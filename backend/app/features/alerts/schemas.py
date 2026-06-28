"""Alert DTOs."""

import uuid
from datetime import datetime

from pydantic import Field

from app.features.alerts.models import AlertSeverity, AlertStatus, AlertType
from app.shared.schemas import BaseSchema


class AlertCreate(BaseSchema):
    """Manually raised alert."""

    hotel_id: uuid.UUID | None = None
    bin_id: uuid.UUID | None = None
    type: AlertType = AlertType.CUSTOM
    severity: AlertSeverity = AlertSeverity.WARNING
    title: str = Field(min_length=1, max_length=255)
    message: str | None = None


class AlertRead(BaseSchema):
    id: uuid.UUID
    hotel_id: uuid.UUID | None
    bin_id: uuid.UUID | None
    type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: str | None
    context: dict | None
    acknowledged_by: uuid.UUID | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

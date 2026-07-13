"""Notification DTOs."""

import uuid
from datetime import datetime

from app.features.notifications.models import NotificationType
from app.shared.schemas import BaseSchema


class NotificationRead(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    title: str
    message: str | None
    request_id: uuid.UUID | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class UnreadCount(BaseSchema):
    unread: int

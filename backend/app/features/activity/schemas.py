"""Activity log DTOs."""

import uuid
from datetime import datetime

from app.shared.schemas import BaseSchema


class ActivityLogRead(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    message: str | None
    context: dict | None
    created_at: datetime

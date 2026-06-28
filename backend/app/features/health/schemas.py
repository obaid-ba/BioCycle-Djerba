"""Health check response contracts."""

from typing import Literal

from app.shared.schemas import BaseSchema

Status = Literal["ok", "degraded"]


class HealthResponse(BaseSchema):
    status: Status
    service: str
    environment: str
    database: Status

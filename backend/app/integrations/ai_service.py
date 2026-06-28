"""Integration layer for the external AI prediction service.

We do NOT build the AI model — we only consume its REST API. This module is the
single boundary between our backend and that service: it owns the HTTP contract,
timeouts, error translation, and tolerant response parsing. Everything else in
the app talks to predictions through `AIServiceClient`, never raw HTTP.
"""

import httpx
from fastapi import status
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.core.config import settings
from app.core.logging import get_logger
from app.shared.exceptions import AppException

logger = get_logger(__name__)


class AIServiceError(AppException):
    """Raised when the AI service is unreachable, slow, or returns bad data."""

    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "ai_service_error"
    message = "The AI prediction service is unavailable."


class PredictionRequest(BaseModel):
    """Payload we send to the AI service."""

    organic_weight_kg: float
    non_organic_weight_kg: float
    total_weight_kg: float
    hotel_id: str
    collected_at: str


class AIPredictionResponse(BaseModel):
    """Tolerant parser for the AI response (we don't own its exact field names)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    energy_kwh: float = Field(
        validation_alias=AliasChoices("predicted_energy_kwh", "energy_kwh", "energy")
    )
    biogas_m3: float = Field(
        validation_alias=AliasChoices("predicted_biogas_m3", "biogas_m3", "biogas")
    )
    co2_saved_kg: float = Field(validation_alias=AliasChoices("co2_saved_kg", "co2_saved", "co2"))
    model_version: str | None = Field(
        default=None,
        validation_alias=AliasChoices("model_version", "version", "model"),
    )


class AIServiceClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/health")
            return response.status_code == status.HTTP_200_OK
        except httpx.HTTPError as exc:
            logger.warning("AI health check failed: %s", exc)
            return False

    async def predict(self, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(f"{self._base_url}/api/predictions", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            raise AIServiceError("The AI prediction service timed out.") from exc
        except httpx.HTTPStatusError as exc:
            raise AIServiceError(
                f"The AI prediction service returned {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise AIServiceError("The AI prediction service is unreachable.") from exc


def get_ai_client() -> AIServiceClient:
    """FastAPI dependency — overridden in tests with a fake client."""
    return AIServiceClient(settings.AI_SERVICE_BASE_URL, settings.AI_SERVICE_TIMEOUT_SECONDS)

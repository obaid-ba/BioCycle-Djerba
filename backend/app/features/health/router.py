"""Health check endpoint.

This slice is intentionally tiny — it's the shape every future feature copies:
a `router.py` that depends on `get_db`, returns typed schemas, and stays thin.
The DB ping turns this into a real readiness probe (used by Docker healthcheck).
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.features.health.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Service readiness")
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    database: str = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        database = "degraded"

    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        service=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        database=database,
    )

"""Dashboard & analytics HTTP layer (read-only aggregates + CSV export)."""

import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.analytics.schemas import (
    DashboardStats,
    TimeseriesBucket,
    WasteDistribution,
)
from app.features.analytics.service import AnalyticsService
from app.features.auth.dependencies import CurrentUser
from app.integrations.ai_service import AIServiceClient, get_ai_client

DbSession = Annotated[AsyncSession, Depends(get_db)]
AIClient = Annotated[AIServiceClient, Depends(get_ai_client)]

dashboard_router = APIRouter()
analytics_router = APIRouter()


@dashboard_router.get("/stats", response_model=DashboardStats, summary="Dashboard KPIs")
async def dashboard_stats(
    current_user: CurrentUser, db: DbSession, ai_client: AIClient
) -> DashboardStats:
    return await AnalyticsService(db).dashboard_stats(current_user, ai_client)


@analytics_router.get(
    "/waste-distribution",
    response_model=WasteDistribution,
    summary="Organic vs non-organic split",
)
async def waste_distribution(
    current_user: CurrentUser,
    db: DbSession,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> WasteDistribution:
    return await AnalyticsService(db).waste_distribution(current_user, date_from, date_to)


@analytics_router.get(
    "/timeseries",
    response_model=list[TimeseriesBucket],
    summary="Bucketed collection totals (day or month)",
)
async def timeseries(
    current_user: CurrentUser,
    db: DbSession,
    granularity: Annotated[Literal["day", "month"], Query()] = "day",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[TimeseriesBucket]:
    now = datetime.now(UTC)
    if date_to is None:
        date_to = now
    if date_from is None:
        date_from = now - timedelta(days=180 if granularity == "month" else 6)
    return await AnalyticsService(db).timeseries(
        current_user, granularity=granularity, date_from=date_from, date_to=date_to
    )


@analytics_router.get("/export", summary="Export collections as CSV")
async def export_collections(
    current_user: CurrentUser,
    db: DbSession,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Response:
    rows = await AnalyticsService(db).export_rows(current_user, date_from, date_to)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "hotel_id",
            "bin_id",
            "collected_at",
            "organic_weight_kg",
            "non_organic_weight_kg",
            "total_weight_kg",
            "notes",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.hotel_id,
                row.bin_id or "",
                row.collected_at.isoformat(),
                row.organic_weight_kg,
                row.non_organic_weight_kg,
                row.organic_weight_kg + row.non_organic_weight_kg,
                row.notes or "",
            ]
        )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=collections.csv"},
    )

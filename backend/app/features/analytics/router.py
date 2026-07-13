"""Dashboard & analytics HTTP layer (read-only aggregates)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.analytics.request_service import RequestAnalyticsService
from app.features.analytics.schemas import (
    DashboardStats,
    HotelRankingRow,
    OperatorRankingRow,
    RequestStats,
    RequestTimeseriesBucket,
    TimeseriesBucket,
    WasteDistribution,
)
from app.features.analytics.service import AnalyticsService
from app.features.auth.dependencies import CurrentUser, require_role
from app.features.auth.models import UserRole
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


@dashboard_router.get(
    "/request-stats",
    response_model=RequestStats,
    summary="Collection-request KPIs (counts by status, weight, methane, quality)",
)
async def request_stats(current_user: CurrentUser, db: DbSession) -> RequestStats:
    return await RequestAnalyticsService(db).request_stats(current_user)


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


@analytics_router.get(
    "/hotel-ranking",
    response_model=list[HotelRankingRow],
    summary="Top hotels by estimated methane",
)
async def hotel_ranking(
    current_user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[HotelRankingRow]:
    return await RequestAnalyticsService(db).hotel_ranking(current_user, limit=limit)


@analytics_router.get(
    "/operator-ranking",
    response_model=list[OperatorRankingRow],
    summary="Operators by requests handled (admin only)",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def operator_ranking(
    current_user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[OperatorRankingRow]:
    return await RequestAnalyticsService(db).operator_ranking(limit=limit)


@analytics_router.get(
    "/requests-timeseries",
    response_model=list[RequestTimeseriesBucket],
    summary="Bucketed request counts / weight / methane (day or month)",
)
async def requests_timeseries(
    current_user: CurrentUser,
    db: DbSession,
    granularity: Annotated[Literal["day", "month"], Query()] = "day",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[RequestTimeseriesBucket]:
    now = datetime.now(UTC)
    if date_to is None:
        date_to = now
    if date_from is None:
        date_from = now - timedelta(days=180 if granularity == "month" else 6)
    return await RequestAnalyticsService(db).timeseries(
        current_user, granularity=granularity, date_from=date_from, date_to=date_to
    )
    # Note: the old /analytics/export (waste_collections CSV) was removed —
    # superseded by /reports/requests.csv on the current data model.

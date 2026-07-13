"""Reports HTTP layer: period summary (JSON) + CSV export of collection requests.

Access is open to all authenticated roles but results are scoped: hotel managers
only ever see their own hotels' requests (enforced in the service).
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.auth.dependencies import CurrentUser
from app.features.reports.schemas import ReportSummary
from app.features.reports.service import ReportService
from app.features.requests.state_machine import RequestStatus

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]

# Shared period params: default to the last 30 days.
DateFrom = Annotated[datetime | None, Query(description="Start of the period (ISO)")]
DateTo = Annotated[datetime | None, Query(description="End of the period (ISO)")]
StatusFilter = Annotated[RequestStatus | None, Query(alias="status")]
HotelFilter = Annotated[uuid.UUID | None, Query()]


def _period(date_from: datetime | None, date_to: datetime | None) -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    return (date_from or now - timedelta(days=30)), (date_to or now)


@router.get("/summary", response_model=ReportSummary, summary="Period summary of requests")
async def report_summary(
    current_user: CurrentUser,
    db: DbSession,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    status_filter: StatusFilter = None,
    hotel_id: HotelFilter = None,
) -> ReportSummary:
    start, end = _period(date_from, date_to)
    return await ReportService(db).summary(
        current_user,
        date_from=start,
        date_to=end,
        status=status_filter,
        hotel_id=hotel_id,
    )


@router.get("/requests.csv", summary="Export requests as CSV")
async def export_requests_csv(
    current_user: CurrentUser,
    db: DbSession,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    status_filter: StatusFilter = None,
    hotel_id: HotelFilter = None,
) -> Response:
    start, end = _period(date_from, date_to)
    content = await ReportService(db).export_csv(
        current_user,
        date_from=start,
        date_to=end,
        status=status_filter,
        hotel_id=hotel_id,
    )
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=collection_requests.csv"},
    )

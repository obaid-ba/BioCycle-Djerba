"""Report business logic: period-scoped summary + CSV export of requests."""

import csv
import io
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import User, UserRole
from app.features.reports.repository import ReportRepository
from app.features.reports.schemas import (
    ReportPeriod,
    ReportSummary,
    ReportTopHotel,
    ReportTotals,
)
from app.features.requests.state_machine import RequestStatus

# Statuses that count as an accepted (not-rejected) decision.
_ACCEPTED = {
    RequestStatus.ACCEPTED,
    RequestStatus.ON_THE_WAY,
    RequestStatus.COLLECTED,
    RequestStatus.COMPLETED,
}

CSV_COLUMNS = [
    "request_id",
    "hotel_name",
    "status",
    "created_at",
    "declared_weight_kg",
    "collected_weight_kg",
    "distance_to_plant_km",
    "ai_priority_score",
    "ai_quality_score",
    "ai_organic_purity",
    "ai_contamination",
    "ai_estimated_methane_m3",
    "ai_estimated_energy_kwh",
    "ai_estimated_co2_kg",
    "rejection_reason",
]


class ReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ReportRepository(db)

    @staticmethod
    def _manager_scope(user: User) -> uuid.UUID | None:
        return user.id if user.role == UserRole.HOTEL_MANAGER else None

    def _filters(
        self,
        user: User,
        *,
        date_from: datetime,
        date_to: datetime,
        status: RequestStatus | None,
        hotel_id: uuid.UUID | None,
    ) -> dict:
        return {
            "manager_id": self._manager_scope(user),
            "date_from": date_from,
            "date_to": date_to,
            "status": status,
            "hotel_id": hotel_id,
        }

    async def summary(
        self,
        user: User,
        *,
        date_from: datetime,
        date_to: datetime,
        status: RequestStatus | None = None,
        hotel_id: uuid.UUID | None = None,
    ) -> ReportSummary:
        kw = self._filters(
            user, date_from=date_from, date_to=date_to, status=status, hotel_id=hotel_id
        )
        totals = await self.repo.totals(**kw)
        counts = await self.repo.status_counts(**kw)

        accepted = sum(counts[s.value] for s in _ACCEPTED)
        rejected = counts[RequestStatus.REJECTED.value]
        decided = accepted + rejected
        acceptance_rate = round(accepted / decided * 100, 1) if decided else None

        # Top hotels by methane, derived from the CSV rows (small result set,
        # avoids a second grouped query for the MVP).
        rows = await self.repo.rows(**kw)
        per_hotel: dict[str, dict] = {}
        for hotel_name, req in rows:
            h = per_hotel.setdefault(hotel_name, {"count": 0, "methane": 0.0})
            h["count"] += 1
            h["methane"] += req.ai_estimated_methane_m3 or 0.0
        top = sorted(per_hotel.items(), key=lambda kv: kv[1]["methane"], reverse=True)[:5]

        return ReportSummary(
            period=ReportPeriod(date_from=date_from, date_to=date_to),
            totals=ReportTotals(
                requests=totals["requests"],
                declared_weight_kg=round(totals["declared_weight_kg"], 3),
                collected_weight_kg=round(totals["collected_weight_kg"], 3),
                estimated_methane_m3=round(totals["estimated_methane_m3"], 3),
                estimated_energy_kwh=round(totals["estimated_energy_kwh"], 3),
                estimated_co2_kg=round(totals["estimated_co2_kg"], 3),
            ),
            status_counts=counts,
            avg_quality_score=(
                round(totals["avg_quality_score"], 1)
                if totals["avg_quality_score"] is not None
                else None
            ),
            acceptance_rate=acceptance_rate,
            top_hotels=[
                ReportTopHotel(
                    hotel_name=name,
                    request_count=v["count"],
                    total_methane_m3=round(v["methane"], 3),
                )
                for name, v in top
            ],
        )

    async def export_csv(
        self,
        user: User,
        *,
        date_from: datetime,
        date_to: datetime,
        status: RequestStatus | None = None,
        hotel_id: uuid.UUID | None = None,
    ) -> str:
        kw = self._filters(
            user, date_from=date_from, date_to=date_to, status=status, hotel_id=hotel_id
        )
        rows = await self.repo.rows(**kw)

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(CSV_COLUMNS)
        for hotel_name, r in rows:
            writer.writerow(
                [
                    r.id,
                    hotel_name,
                    r.status.value,
                    r.created_at.isoformat(),
                    r.declared_weight_kg,
                    r.collected_weight_kg if r.collected_weight_kg is not None else "",
                    r.distance_to_plant_km if r.distance_to_plant_km is not None else "",
                    r.ai_priority_score if r.ai_priority_score is not None else "",
                    r.ai_quality_score if r.ai_quality_score is not None else "",
                    r.ai_organic_purity if r.ai_organic_purity is not None else "",
                    r.ai_contamination if r.ai_contamination is not None else "",
                    r.ai_estimated_methane_m3 if r.ai_estimated_methane_m3 is not None else "",
                    r.ai_estimated_energy_kwh if r.ai_estimated_energy_kwh is not None else "",
                    r.ai_estimated_co2_kg if r.ai_estimated_co2_kg is not None else "",
                    r.rejection_reason or "",
                ]
            )
        return buffer.getvalue()

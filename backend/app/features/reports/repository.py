"""Period-scoped aggregation + row queries for reports.

Self-contained (doesn't reuse AnalyticsRepository) so report date-filtering never
perturbs the live dashboard. Portable SQL (SUM/COUNT/AVG/GROUP BY), matching the
project's other aggregation code.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select

from app.features.hotels.models import Hotel
from app.features.requests.models import CollectionRequest
from app.features.requests.state_machine import RequestStatus


class ReportRepository:
    def __init__(self, db) -> None:
        self.db = db

    def _apply_scope_and_period(
        self,
        stmt,
        *,
        manager_id: uuid.UUID | None,
        date_from: datetime,
        date_to: datetime,
        status: RequestStatus | None,
        hotel_id: uuid.UUID | None,
    ):
        stmt = stmt.where(
            CollectionRequest.created_at >= date_from,
            CollectionRequest.created_at <= date_to,
        )
        if status is not None:
            stmt = stmt.where(CollectionRequest.status == status)
        if hotel_id is not None:
            stmt = stmt.where(CollectionRequest.hotel_id == hotel_id)
        # Hotel managers only ever see their own hotels' requests.
        if manager_id is not None:
            stmt = stmt.join(Hotel, CollectionRequest.hotel_id == Hotel.id).where(
                Hotel.manager_id == manager_id
            )
        return stmt

    async def totals(self, **kw) -> dict:
        stmt = select(
            func.count(CollectionRequest.id),
            func.coalesce(func.sum(CollectionRequest.declared_weight_kg), 0.0),
            func.coalesce(func.sum(CollectionRequest.collected_weight_kg), 0.0),
            func.coalesce(func.sum(CollectionRequest.ai_estimated_methane_m3), 0.0),
            func.coalesce(func.sum(CollectionRequest.ai_estimated_energy_kwh), 0.0),
            func.coalesce(func.sum(CollectionRequest.ai_estimated_co2_kg), 0.0),
            func.avg(CollectionRequest.ai_quality_score),
        )
        stmt = self._apply_scope_and_period(stmt, **kw)
        count, declared, collected, methane, energy, co2, avg_q = (
            await self.db.execute(stmt)
        ).one()
        return {
            "requests": int(count),
            "declared_weight_kg": float(declared),
            "collected_weight_kg": float(collected),
            "estimated_methane_m3": float(methane),
            "estimated_energy_kwh": float(energy),
            "estimated_co2_kg": float(co2),
            "avg_quality_score": float(avg_q) if avg_q is not None else None,
        }

    async def status_counts(self, **kw) -> dict[str, int]:
        stmt = select(
            CollectionRequest.status, func.count(CollectionRequest.id)
        ).group_by(CollectionRequest.status)
        stmt = self._apply_scope_and_period(stmt, **kw)
        rows = (await self.db.execute(stmt)).all()
        counts = {s.value: 0 for s in RequestStatus}
        for status, count in rows:
            key = status.value if hasattr(status, "value") else str(status)
            counts[key] = int(count)
        return counts

    async def rows(self, **kw) -> Sequence[tuple]:
        """Ordered (hotel_name, request) pairs for the CSV export."""
        stmt = select(Hotel.name, CollectionRequest).join(
            Hotel, CollectionRequest.hotel_id == Hotel.id
        )
        # _apply_scope_and_period may add its own join for scoped managers; here
        # the base query already joins Hotel, so scope via a where on manager_id.
        stmt = stmt.where(
            CollectionRequest.created_at >= kw["date_from"],
            CollectionRequest.created_at <= kw["date_to"],
        )
        if kw.get("status") is not None:
            stmt = stmt.where(CollectionRequest.status == kw["status"])
        if kw.get("hotel_id") is not None:
            stmt = stmt.where(CollectionRequest.hotel_id == kw["hotel_id"])
        if kw.get("manager_id") is not None:
            stmt = stmt.where(Hotel.manager_id == kw["manager_id"])
        stmt = stmt.order_by(CollectionRequest.created_at.asc())
        return (await self.db.execute(stmt)).all()

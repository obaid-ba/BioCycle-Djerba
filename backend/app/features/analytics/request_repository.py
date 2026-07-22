"""Aggregation queries over collection_requests for the (request-centric) dashboard.

The product's metrics now derive from Collection Requests, not the legacy
waste_collections table. Uses portable SUM/COUNT/AVG/GROUP BY (no date_trunc);
time-bucketing is done in Python by the service, matching AnalyticsRepository.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import User
from app.features.hotels.models import Hotel
from app.features.requests.models import CollectionRequest
from app.features.requests.state_machine import RequestStatus


class RequestAnalyticsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _scoped(self, stmt, manager_id: uuid.UUID | None):
        """Restrict to a manager's own hotels when scoped."""
        if manager_id is not None:
            stmt = stmt.join(Hotel, CollectionRequest.hotel_id == Hotel.id).where(
                Hotel.manager_id == manager_id
            )
        return stmt

    async def status_counts(
        self, *, manager_id: uuid.UUID | None
    ) -> dict[str, int]:
        """Number of requests in each lifecycle status (all statuses present)."""
        stmt = select(
            CollectionRequest.status, func.count(CollectionRequest.id)
        ).group_by(CollectionRequest.status)
        stmt = self._scoped(stmt, manager_id)
        rows = (await self.db.execute(stmt)).all()

        # Start from zero for every status so the UI always has a full set.
        counts = {status.value: 0 for status in RequestStatus}
        for status, count in rows:
            key = status.value if hasattr(status, "value") else str(status)
            counts[key] = int(count)
        return counts

    async def aggregate_totals(
        self, *, manager_id: uuid.UUID | None
    ) -> dict[str, float]:
        """Weight, AI-estimated energy/methane/CO2, and average quality."""
        stmt = select(
            func.count(CollectionRequest.id),
            func.coalesce(func.sum(CollectionRequest.declared_weight_kg), 0.0),
            func.coalesce(func.sum(CollectionRequest.collected_weight_kg), 0.0),
            func.coalesce(func.sum(CollectionRequest.ai_estimated_methane_m3), 0.0),
            func.coalesce(func.sum(CollectionRequest.ai_estimated_energy_kwh), 0.0),
            func.coalesce(func.sum(CollectionRequest.ai_estimated_co2_kg), 0.0),
            func.avg(CollectionRequest.ai_quality_score),
        )
        stmt = self._scoped(stmt, manager_id)
        row = (await self.db.execute(stmt)).one()
        total, declared, collected, methane, energy, co2, avg_quality = row
        return {
            "total_requests": int(total),
            "declared_weight_kg": float(declared),
            "collected_weight_kg": float(collected),
            "estimated_methane_m3": float(methane),
            "estimated_energy_kwh": float(energy),
            "estimated_co2_kg": float(co2),
            "avg_quality_score": float(avg_quality) if avg_quality is not None else None,
        }

    async def purity_split(
        self, *, manager_id: uuid.UUID | None
    ) -> dict[str, float]:
        """Declared weight split into usable organic mass vs contamination.

        The AI reports `ai_organic_purity` as a percentage of each load; the
        usable mass is weight × purity, and the rest is contamination. Only rows
        the AI actually scored are included — an unscored request has no known
        split, and assuming one would invent data.
        """
        purity_fraction = CollectionRequest.ai_organic_purity / 100.0
        stmt = select(
            func.coalesce(
                func.sum(CollectionRequest.declared_weight_kg * purity_fraction), 0.0
            ),
            func.coalesce(
                func.sum(CollectionRequest.declared_weight_kg * (1 - purity_fraction)),
                0.0,
            ),
        ).where(CollectionRequest.ai_organic_purity.is_not(None))
        stmt = self._scoped(stmt, manager_id)
        organic, contamination = (await self.db.execute(stmt)).one()
        return {"organic_kg": float(organic), "contamination_kg": float(contamination)}

    async def hotel_ranking(
        self, *, manager_id: uuid.UUID | None, limit: int = 10
    ) -> Sequence[tuple]:
        """Per-hotel rollup, ranked by total estimated methane (desc).

        Returns rows of (hotel_id, hotel_name, request_count, total_weight,
        total_methane, avg_quality).
        """
        stmt = (
            select(
                Hotel.id,
                Hotel.name,
                func.count(CollectionRequest.id),
                func.coalesce(func.sum(CollectionRequest.declared_weight_kg), 0.0),
                func.coalesce(func.sum(CollectionRequest.ai_estimated_methane_m3), 0.0),
                func.avg(CollectionRequest.ai_quality_score),
            )
            .join(Hotel, CollectionRequest.hotel_id == Hotel.id)
            .group_by(Hotel.id, Hotel.name)
            .order_by(
                func.coalesce(func.sum(CollectionRequest.ai_estimated_methane_m3), 0.0).desc()
            )
            .limit(limit)
        )
        if manager_id is not None:
            stmt = stmt.where(Hotel.manager_id == manager_id)
        return (await self.db.execute(stmt)).all()

    async def operator_ranking(self, *, limit: int = 10) -> Sequence[tuple]:
        """Per-operator rollup of decided requests, ranked by volume handled.

        Only requests that have been decided (decided_by set) count. Returns
        (operator_id, operator_name, decided_count, completed_count).
        """
        # Portable "count of completed" via CASE ... SUM (works on SQLite + PG).
        completed_count = func.sum(
            case((CollectionRequest.status == RequestStatus.COMPLETED, 1), else_=0)
        )
        stmt = (
            select(
                User.id,
                User.full_name,
                func.count(CollectionRequest.id),
                completed_count,
            )
            .join(User, CollectionRequest.decided_by == User.id)
            .group_by(User.id, User.full_name)
            .order_by(func.count(CollectionRequest.id).desc())
            .limit(limit)
        )
        return (await self.db.execute(stmt)).all()

    async def requests_in_range(
        self,
        *,
        manager_id: uuid.UUID | None,
        date_from: datetime,
        date_to: datetime,
    ) -> Sequence[CollectionRequest]:
        stmt = select(CollectionRequest).where(
            CollectionRequest.created_at >= date_from,
            CollectionRequest.created_at <= date_to,
        )
        stmt = self._scoped(stmt, manager_id)
        stmt = stmt.order_by(CollectionRequest.created_at.asc())
        return (await self.db.execute(stmt)).scalars().all()

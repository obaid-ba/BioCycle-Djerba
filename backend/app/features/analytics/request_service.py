"""Request-centric analytics service — KPIs, rankings, timeseries.

Derives every metric from collection_requests (the current product's source of
truth). Reuses the day/month bucketing helpers from the legacy analytics service
so behavior stays consistent.
"""

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.analytics.request_repository import RequestAnalyticsRepository
from app.features.analytics.schemas import (
    HotelRankingRow,
    OperatorRankingRow,
    PuritySplit,
    RequestStats,
    RequestTimeseriesBucket,
)
from app.features.analytics.service import _bucket_key, _iter_bucket_keys
from app.features.auth.models import User, UserRole
from app.features.requests.state_machine import RequestStatus

# Statuses that represent a "yes" decision (for the acceptance rate).
_ACCEPTED_STATUSES = {
    RequestStatus.ACCEPTED,
    RequestStatus.ON_THE_WAY,
    RequestStatus.COLLECTED,
    RequestStatus.COMPLETED,
}


class RequestAnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = RequestAnalyticsRepository(db)

    @staticmethod
    def _manager_scope(user: User) -> uuid.UUID | None:
        return user.id if user.role == UserRole.HOTEL_MANAGER else None

    async def request_stats(self, user: User) -> RequestStats:
        scope = self._manager_scope(user)
        counts = await self.repo.status_counts(manager_id=scope)
        totals = await self.repo.aggregate_totals(manager_id=scope)

        accepted = sum(counts[s.value] for s in _ACCEPTED_STATUSES)
        rejected = counts[RequestStatus.REJECTED.value]
        decided = accepted + rejected
        acceptance_rate = round(accepted / decided * 100, 1) if decided > 0 else None

        avg_q = totals["avg_quality_score"]
        return RequestStats(
            total_requests=totals["total_requests"],
            status_counts=counts,
            declared_weight_kg=round(totals["declared_weight_kg"], 3),
            collected_weight_kg=round(totals["collected_weight_kg"], 3),
            estimated_methane_m3=round(totals["estimated_methane_m3"], 3),
            estimated_energy_kwh=round(totals["estimated_energy_kwh"], 3),
            estimated_co2_kg=round(totals["estimated_co2_kg"], 3),
            avg_quality_score=round(avg_q, 1) if avg_q is not None else None,
            acceptance_rate=acceptance_rate,
        )

    async def purity_split(self, user: User) -> PuritySplit:
        """Usable organic mass vs contamination across all scored requests."""
        split = await self.repo.purity_split(manager_id=self._manager_scope(user))
        organic = split["organic_kg"]
        total = organic + split["contamination_kg"]
        return PuritySplit(
            organic_kg=round(organic, 3),
            contamination_kg=round(split["contamination_kg"], 3),
            total_kg=round(total, 3),
            organic_percentage=round(organic / total * 100, 1) if total > 0 else None,
        )

    async def hotel_ranking(self, user: User, limit: int = 10) -> list[HotelRankingRow]:
        scope = self._manager_scope(user)
        rows = await self.repo.hotel_ranking(manager_id=scope, limit=limit)
        return [
            HotelRankingRow(
                hotel_id=str(hid),
                hotel_name=name,
                request_count=int(count),
                total_weight_kg=round(float(weight), 3),
                total_methane_m3=round(float(methane), 3),
                avg_quality_score=round(float(avg_q), 1) if avg_q is not None else None,
            )
            for hid, name, count, weight, methane, avg_q in rows
        ]

    async def operator_ranking(self, limit: int = 10) -> list[OperatorRankingRow]:
        rows = await self.repo.operator_ranking(limit=limit)
        return [
            OperatorRankingRow(
                operator_id=str(oid),
                operator_name=name,
                handled_count=int(handled),
                completed_count=int(completed),
            )
            for oid, name, handled, completed in rows
        ]

    async def timeseries(
        self,
        user: User,
        *,
        granularity: str,
        date_from: datetime,
        date_to: datetime,
    ) -> list[RequestTimeseriesBucket]:
        scope = self._manager_scope(user)
        rows = await self.repo.requests_in_range(
            manager_id=scope, date_from=date_from, date_to=date_to
        )

        buckets: dict[str, dict] = {
            key: {"count": 0, "weight": 0.0, "methane": 0.0}
            for key in _iter_bucket_keys(date_from, date_to, granularity)
        }
        for row in rows:
            key = _bucket_key(row.created_at, granularity)
            bucket = buckets.setdefault(key, {"count": 0, "weight": 0.0, "methane": 0.0})
            bucket["count"] += 1
            bucket["weight"] += row.declared_weight_kg or 0.0
            bucket["methane"] += row.ai_estimated_methane_m3 or 0.0

        return [
            RequestTimeseriesBucket(
                bucket=key,
                count=v["count"],
                declared_weight_kg=round(v["weight"], 3),
                estimated_methane_m3=round(v["methane"], 3),
            )
            for key, v in sorted(buckets.items())
        ]

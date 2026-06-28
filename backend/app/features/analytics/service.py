"""Analytics & dashboard service: aggregation, bucketing, system status."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.features.analytics.repository import AnalyticsRepository
from app.features.analytics.schemas import (
    DashboardStats,
    SystemStatus,
    TimeseriesBucket,
    WasteDistribution,
)
from app.features.auth.models import User, UserRole
from app.features.bins.models import BinStatus
from app.features.collections.models import WasteCollection
from app.integrations.ai_service import AIServiceClient
from app.mqtt.consumer import is_mqtt_connected
from app.realtime.manager import manager


def _start_of_today() -> datetime:
    now = datetime.now(UTC)
    return datetime(now.year, now.month, now.day, tzinfo=UTC)


def _bucket_key(dt: datetime, granularity: str) -> str:
    if granularity == "month":
        return f"{dt.year:04d}-{dt.month:02d}"
    return dt.date().isoformat()


def _iter_bucket_keys(date_from: datetime, date_to: datetime, granularity: str) -> list[str]:
    keys: list[str] = []
    if granularity == "month":
        year, month = date_from.year, date_from.month
        while (year, month) <= (date_to.year, date_to.month):
            keys.append(f"{year:04d}-{month:02d}")
            month += 1
            if month > 12:
                month = 1
                year += 1
    else:
        day = date_from.date()
        end = date_to.date()
        while day <= end:
            keys.append(day.isoformat())
            day += timedelta(days=1)
    return keys


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AnalyticsRepository(db)

    @staticmethod
    def _manager_scope(user: User) -> uuid.UUID | None:
        return user.id if user.role == UserRole.HOTEL_MANAGER else None

    async def dashboard_stats(self, user: User, ai_client: AIServiceClient) -> DashboardStats:
        scope = self._manager_scope(user)
        today = _start_of_today()

        count, organic, non_organic = await self.repo.collection_totals(
            manager_id=scope, date_from=today
        )
        energy, biogas, co2 = await self.repo.prediction_totals(manager_id=scope, date_from=today)
        hotels = await self.repo.count_hotels(manager_id=scope)
        total_bins = await self.repo.count_bins(manager_id=scope)
        online_bins = await self.repo.count_bins(manager_id=scope, status=BinStatus.ONLINE)
        open_alerts = await self.repo.count_open_alerts(manager_id=scope)

        return DashboardStats(
            today_collections=count,
            organic_waste_kg=round(organic, 3),
            non_organic_waste_kg=round(non_organic, 3),
            total_waste_kg=round(organic + non_organic, 3),
            predicted_energy_kwh=round(energy, 3),
            predicted_biogas_m3=round(biogas, 3),
            co2_saved_kg=round(co2, 3),
            hotels_connected=hotels,
            total_bins=total_bins,
            online_bins=online_bins,
            open_alerts=open_alerts,
            system=await self._system_status(ai_client),
        )

    async def _system_status(self, ai_client: AIServiceClient) -> SystemStatus:
        ai_ok = await ai_client.health()
        if not settings.MQTT_ENABLED:
            mqtt = "disabled"
        else:
            mqtt = "online" if is_mqtt_connected() else "offline"
        return SystemStatus(
            ai="online" if ai_ok else "offline",
            mqtt=mqtt,
            websocket="online",
            websocket_connections=manager.count,
        )

    async def waste_distribution(
        self,
        user: User,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> WasteDistribution:
        scope = self._manager_scope(user)
        _, organic, non_organic = await self.repo.collection_totals(
            manager_id=scope, date_from=date_from, date_to=date_to
        )
        total = organic + non_organic
        return WasteDistribution(
            organic_kg=round(organic, 3),
            non_organic_kg=round(non_organic, 3),
            total_kg=round(total, 3),
            organic_percentage=round(organic / total * 100, 1) if total > 0 else None,
        )

    async def timeseries(
        self,
        user: User,
        *,
        granularity: str,
        date_from: datetime,
        date_to: datetime,
    ) -> list[TimeseriesBucket]:
        scope = self._manager_scope(user)
        rows = await self.repo.collections_in_range(
            manager_id=scope, date_from=date_from, date_to=date_to
        )

        buckets: dict[str, dict] = {
            key: {"count": 0, "organic": 0.0, "non_organic": 0.0}
            for key in _iter_bucket_keys(date_from, date_to, granularity)
        }
        for row in rows:
            key = _bucket_key(row.collected_at, granularity)
            bucket = buckets.setdefault(key, {"count": 0, "organic": 0.0, "non_organic": 0.0})
            bucket["count"] += 1
            bucket["organic"] += row.organic_weight_kg
            bucket["non_organic"] += row.non_organic_weight_kg

        return [
            TimeseriesBucket(
                bucket=key,
                count=value["count"],
                organic_kg=round(value["organic"], 3),
                non_organic_kg=round(value["non_organic"], 3),
                total_kg=round(value["organic"] + value["non_organic"], 3),
            )
            for key, value in sorted(buckets.items())
        ]

    async def export_rows(
        self,
        user: User,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[WasteCollection]:
        scope = self._manager_scope(user)
        return list(
            await self.repo.collections_in_range(
                manager_id=scope, date_from=date_from, date_to=date_to
            )
        )

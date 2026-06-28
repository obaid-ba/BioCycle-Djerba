"""Aggregation queries for analytics and dashboard.

Uses SUM/COUNT in SQL (portable across Postgres and SQLite). Time-bucketing is
done in Python by the service, so we deliberately avoid `date_trunc` here.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.alerts.models import Alert, AlertStatus
from app.features.bins.models import BinStatus, SmartBin
from app.features.collections.models import (
    Prediction,
    PredictionStatus,
    WasteCollection,
)
from app.features.hotels.models import Hotel


class AnalyticsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def collection_totals(
        self,
        *,
        manager_id: uuid.UUID | None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[int, float, float]:
        stmt = select(
            func.count(WasteCollection.id),
            func.coalesce(func.sum(WasteCollection.organic_weight_kg), 0.0),
            func.coalesce(func.sum(WasteCollection.non_organic_weight_kg), 0.0),
        )
        if manager_id is not None:
            stmt = stmt.join(Hotel, WasteCollection.hotel_id == Hotel.id).where(
                Hotel.manager_id == manager_id
            )
        if date_from is not None:
            stmt = stmt.where(WasteCollection.collected_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(WasteCollection.collected_at <= date_to)
        count, organic, non_organic = (await self.db.execute(stmt)).one()
        return int(count), float(organic), float(non_organic)

    async def prediction_totals(
        self,
        *,
        manager_id: uuid.UUID | None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[float, float, float]:
        stmt = (
            select(
                func.coalesce(func.sum(Prediction.predicted_energy_kwh), 0.0),
                func.coalesce(func.sum(Prediction.predicted_biogas_m3), 0.0),
                func.coalesce(func.sum(Prediction.co2_saved_kg), 0.0),
            )
            .select_from(Prediction)
            .join(WasteCollection, Prediction.collection_id == WasteCollection.id)
            .where(Prediction.status == PredictionStatus.SUCCESS)
        )
        if manager_id is not None:
            stmt = stmt.join(Hotel, WasteCollection.hotel_id == Hotel.id).where(
                Hotel.manager_id == manager_id
            )
        if date_from is not None:
            stmt = stmt.where(WasteCollection.collected_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(WasteCollection.collected_at <= date_to)
        energy, biogas, co2 = (await self.db.execute(stmt)).one()
        return float(energy), float(biogas), float(co2)

    async def count_hotels(self, *, manager_id: uuid.UUID | None) -> int:
        stmt = select(func.count(Hotel.id))
        if manager_id is not None:
            stmt = stmt.where(Hotel.manager_id == manager_id)
        return int((await self.db.execute(stmt)).scalar_one())

    async def count_bins(
        self, *, manager_id: uuid.UUID | None, status: BinStatus | None = None
    ) -> int:
        stmt = select(func.count(SmartBin.id))
        if manager_id is not None:
            stmt = stmt.join(Hotel, SmartBin.hotel_id == Hotel.id).where(
                Hotel.manager_id == manager_id
            )
        if status is not None:
            stmt = stmt.where(SmartBin.status == status)
        return int((await self.db.execute(stmt)).scalar_one())

    async def count_open_alerts(self, *, manager_id: uuid.UUID | None) -> int:
        stmt = select(func.count(Alert.id)).where(Alert.status == AlertStatus.OPEN)
        if manager_id is not None:
            stmt = stmt.join(Hotel, Alert.hotel_id == Hotel.id).where(
                Hotel.manager_id == manager_id
            )
        return int((await self.db.execute(stmt)).scalar_one())

    async def collections_in_range(
        self,
        *,
        manager_id: uuid.UUID | None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Sequence[WasteCollection]:
        stmt = select(WasteCollection)
        if manager_id is not None:
            stmt = stmt.join(Hotel, WasteCollection.hotel_id == Hotel.id).where(
                Hotel.manager_id == manager_id
            )
        if date_from is not None:
            stmt = stmt.where(WasteCollection.collected_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(WasteCollection.collected_at <= date_to)
        stmt = stmt.order_by(WasteCollection.collected_at.asc())
        return (await self.db.execute(stmt)).scalars().all()

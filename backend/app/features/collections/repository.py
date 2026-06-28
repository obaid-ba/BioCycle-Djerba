"""Data access for waste collections and predictions."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select

from app.features.collections.models import Prediction, WasteCollection
from app.features.hotels.models import Hotel
from app.shared.repository import BaseRepository
from app.shared.schemas import PaginationParams
from app.shared.sorting import build_order_by

COLLECTION_SORTABLE = {
    "collected_at": WasteCollection.collected_at,
    "organic_weight_kg": WasteCollection.organic_weight_kg,
    "non_organic_weight_kg": WasteCollection.non_organic_weight_kg,
    "created_at": WasteCollection.created_at,
}


class CollectionRepository(BaseRepository[WasteCollection]):
    model = WasteCollection

    async def search(
        self,
        *,
        params: PaginationParams,
        hotel_id: uuid.UUID | None = None,
        bin_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort: str | None = None,
        manager_id: uuid.UUID | None = None,
    ) -> tuple[Sequence[WasteCollection], int]:
        stmt = select(WasteCollection)
        count_stmt = select(func.count()).select_from(WasteCollection)

        if manager_id is not None:
            join_cond = WasteCollection.hotel_id == Hotel.id
            stmt = stmt.join(Hotel, join_cond).where(Hotel.manager_id == manager_id)
            count_stmt = count_stmt.join(Hotel, join_cond).where(Hotel.manager_id == manager_id)
        if hotel_id is not None:
            stmt = stmt.where(WasteCollection.hotel_id == hotel_id)
            count_stmt = count_stmt.where(WasteCollection.hotel_id == hotel_id)
        if bin_id is not None:
            stmt = stmt.where(WasteCollection.bin_id == bin_id)
            count_stmt = count_stmt.where(WasteCollection.bin_id == bin_id)
        if date_from is not None:
            stmt = stmt.where(WasteCollection.collected_at >= date_from)
            count_stmt = count_stmt.where(WasteCollection.collected_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(WasteCollection.collected_at <= date_to)
            count_stmt = count_stmt.where(WasteCollection.collected_at <= date_to)

        order_by = build_order_by(sort, COLLECTION_SORTABLE, WasteCollection.collected_at.desc())
        stmt = stmt.order_by(order_by).offset(params.offset).limit(params.limit)

        items = (await self.db.execute(stmt)).scalars().all()
        total = int((await self.db.execute(count_stmt)).scalar_one())
        return items, total


class PredictionRepository(BaseRepository[Prediction]):
    model = Prediction

    async def list_for_collection(
        self, collection_id: uuid.UUID, params: PaginationParams
    ) -> tuple[Sequence[Prediction], int]:
        filters = [Prediction.collection_id == collection_id]
        items = await self.list(
            offset=params.offset,
            limit=params.limit,
            order_by=Prediction.created_at.desc(),
            filters=filters,
        )
        total = await self.count(filters=filters)
        return items, total

    async def latest_for_collection(self, collection_id: uuid.UUID) -> Prediction | None:
        stmt = (
            select(Prediction)
            .where(Prediction.collection_id == collection_id)
            .order_by(Prediction.created_at.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

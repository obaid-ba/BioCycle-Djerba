"""Data access for smart bins and sensor readings."""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select

from app.features.bins.models import BinStatus, BinType, SensorReading, SmartBin
from app.features.hotels.models import Hotel
from app.shared.repository import BaseRepository
from app.shared.schemas import PaginationParams
from app.shared.sorting import build_order_by

BIN_SORTABLE = {
    "code": SmartBin.code,
    "name": SmartBin.name,
    "status": SmartBin.status,
    "fill_level": SmartBin.fill_level,
    "battery_level": SmartBin.battery_level,
    "last_reading_at": SmartBin.last_reading_at,
    "created_at": SmartBin.created_at,
}


class BinRepository(BaseRepository[SmartBin]):
    model = SmartBin

    async def get_by_code(self, code: str) -> SmartBin | None:
        result = await self.db.execute(select(SmartBin).where(SmartBin.code == code))
        return result.scalar_one_or_none()

    async def search(
        self,
        *,
        params: PaginationParams,
        search: str | None = None,
        hotel_id: uuid.UUID | None = None,
        status: BinStatus | None = None,
        bin_type: BinType | None = None,
        sort: str | None = None,
        manager_id: uuid.UUID | None = None,
    ) -> tuple[Sequence[SmartBin], int]:
        stmt = select(SmartBin)
        count_stmt = select(func.count()).select_from(SmartBin)

        # Scope to a manager's hotels by joining hotels.manager_id.
        if manager_id is not None:
            stmt = stmt.join(Hotel, SmartBin.hotel_id == Hotel.id).where(
                Hotel.manager_id == manager_id
            )
            count_stmt = count_stmt.join(Hotel, SmartBin.hotel_id == Hotel.id).where(
                Hotel.manager_id == manager_id
            )

        if search:
            like = f"%{search}%"
            condition = SmartBin.code.ilike(like) | SmartBin.name.ilike(like)
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)
        if hotel_id is not None:
            stmt = stmt.where(SmartBin.hotel_id == hotel_id)
            count_stmt = count_stmt.where(SmartBin.hotel_id == hotel_id)
        if status is not None:
            stmt = stmt.where(SmartBin.status == status)
            count_stmt = count_stmt.where(SmartBin.status == status)
        if bin_type is not None:
            stmt = stmt.where(SmartBin.bin_type == bin_type)
            count_stmt = count_stmt.where(SmartBin.bin_type == bin_type)

        order_by = build_order_by(sort, BIN_SORTABLE, SmartBin.created_at.desc())
        stmt = stmt.order_by(order_by).offset(params.offset).limit(params.limit)

        items = (await self.db.execute(stmt)).scalars().all()
        total = int((await self.db.execute(count_stmt)).scalar_one())
        return items, total


class SensorReadingRepository(BaseRepository[SensorReading]):
    model = SensorReading

    async def list_for_bin(
        self, bin_id: uuid.UUID, params: PaginationParams
    ) -> tuple[Sequence[SensorReading], int]:
        filters = [SensorReading.bin_id == bin_id]
        items = await self.list(
            offset=params.offset,
            limit=params.limit,
            order_by=SensorReading.recorded_at.desc(),
            filters=filters,
        )
        total = await self.count(filters=filters)
        return items, total

    async def latest_for_bin(self, bin_id: uuid.UUID) -> SensorReading | None:
        stmt = (
            select(SensorReading)
            .where(SensorReading.bin_id == bin_id)
            .order_by(SensorReading.recorded_at.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

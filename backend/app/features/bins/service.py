"""Smart bin business logic, including the reading-ingest path reused by MQTT."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import User, UserRole
from app.features.bins.models import BinStatus, SensorReading, SmartBin
from app.features.bins.repository import BinRepository, SensorReadingRepository
from app.features.bins.schemas import (
    SensorReadingCreate,
    SensorReadingRead,
    SmartBinCreate,
    SmartBinRead,
    SmartBinUpdate,
)
from app.features.hotels.repository import HotelRepository
from app.shared.exceptions import ConflictError, NotFoundError, ValidationError
from app.shared.schemas import Page, PaginationParams


class BinService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.bins = BinRepository(db)
        self.readings = SensorReadingRepository(db)
        self.hotels = HotelRepository(db)

    @staticmethod
    def _manager_scope(user: User) -> uuid.UUID | None:
        return user.id if user.role == UserRole.HOTEL_MANAGER else None

    async def _assert_hotel_exists(self, hotel_id: uuid.UUID) -> None:
        if await self.hotels.get(hotel_id) is None:
            raise ValidationError("Referenced hotel does not exist")

    async def get_or_404(self, bin_id: uuid.UUID, user: User) -> SmartBin:
        bin_ = await self.bins.get(bin_id)
        if bin_ is None:
            raise NotFoundError("Smart bin not found")
        scope = self._manager_scope(user)
        if scope is not None:
            hotel = await self.hotels.get(bin_.hotel_id)
            if hotel is None or hotel.manager_id != scope:
                raise NotFoundError("Smart bin not found")
        return bin_

    async def list(
        self,
        *,
        params: PaginationParams,
        user: User,
        search: str | None = None,
        hotel_id: uuid.UUID | None = None,
        status: BinStatus | None = None,
        bin_type=None,
        sort: str | None = None,
    ) -> Page[SmartBinRead]:
        items, total = await self.bins.search(
            params=params,
            search=search,
            hotel_id=hotel_id,
            status=status,
            bin_type=bin_type,
            sort=sort,
            manager_id=self._manager_scope(user),
        )
        return Page.create([SmartBinRead.model_validate(b) for b in items], total, params)

    async def create(self, data: SmartBinCreate, user: User) -> SmartBin:
        await self._assert_hotel_exists(data.hotel_id)
        if await self.bins.get_by_code(data.code) is not None:
            raise ConflictError("A bin with this code already exists")
        bin_ = SmartBin(**data.model_dump())
        bin_ = await self.bins.add(bin_)
        await self.db.commit()
        await self.db.refresh(bin_)
        return bin_

    async def update(self, bin_id: uuid.UUID, data: SmartBinUpdate, user: User) -> SmartBin:
        bin_ = await self.get_or_404(bin_id, user)
        changes = data.model_dump(exclude_unset=True)
        if "hotel_id" in changes:
            await self._assert_hotel_exists(changes["hotel_id"])
        if "code" in changes and changes["code"] != bin_.code:
            if await self.bins.get_by_code(changes["code"]) is not None:
                raise ConflictError("A bin with this code already exists")
        for field, value in changes.items():
            setattr(bin_, field, value)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(bin_)
        return bin_

    async def delete(self, bin_id: uuid.UUID, user: User) -> None:
        bin_ = await self.get_or_404(bin_id, user)
        await self.bins.delete(bin_)
        await self.db.commit()

    async def list_readings(
        self, bin_id: uuid.UUID, params: PaginationParams, user: User
    ) -> Page[SensorReadingRead]:
        await self.get_or_404(bin_id, user)
        items, total = await self.readings.list_for_bin(bin_id, params)
        return Page.create([SensorReadingRead.model_validate(r) for r in items], total, params)

    async def latest_reading(self, bin_id: uuid.UUID, user: User) -> SensorReading:
        await self.get_or_404(bin_id, user)
        reading = await self.readings.latest_for_bin(bin_id)
        if reading is None:
            raise NotFoundError("No readings recorded for this bin yet")
        return reading

    async def ingest_reading(self, bin_id: uuid.UUID, data: SensorReadingCreate) -> SensorReading:
        """Persist a reading and refresh the bin's cached telemetry.

        Shared by the HTTP ingest endpoint and (Phase 4) the MQTT consumer, so
        it intentionally takes no user — ingestion is a system/device action.
        """
        bin_ = await self.bins.get(bin_id)
        if bin_ is None:
            raise NotFoundError("Smart bin not found")

        recorded_at = data.recorded_at or datetime.now(UTC)
        reading = SensorReading(
            bin_id=bin_id,
            fill_level=data.fill_level,
            weight_kg=data.weight_kg,
            temperature_c=data.temperature_c,
            humidity=data.humidity,
            battery_level=data.battery_level,
            recorded_at=recorded_at,
        )
        await self.readings.add(reading)

        bin_.fill_level = data.fill_level
        if data.battery_level is not None:
            bin_.battery_level = data.battery_level
        bin_.last_reading_at = recorded_at
        bin_.status = BinStatus.ONLINE

        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(reading)
        await self.db.refresh(bin_)
        return reading

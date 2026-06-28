"""Data access for hotels, including search/filter/sort query building."""

import uuid
from collections.abc import Sequence

from sqlalchemy.sql import ColumnExpressionArgument

from app.features.hotels.models import Hotel, HotelStatus
from app.shared.repository import BaseRepository
from app.shared.schemas import PaginationParams
from app.shared.sorting import build_order_by

SORTABLE = {
    "name": Hotel.name,
    "city": Hotel.city,
    "status": Hotel.status,
    "number_of_rooms": Hotel.number_of_rooms,
    "created_at": Hotel.created_at,
}


class HotelRepository(BaseRepository[Hotel]):
    model = Hotel

    @staticmethod
    def _build_filters(
        *,
        search: str | None,
        status: HotelStatus | None,
        manager_id: uuid.UUID | None,
    ) -> list[ColumnExpressionArgument[bool]]:
        filters: list[ColumnExpressionArgument[bool]] = []
        if search:
            like = f"%{search}%"
            filters.append(Hotel.name.ilike(like) | Hotel.city.ilike(like))
        if status is not None:
            filters.append(Hotel.status == status)
        if manager_id is not None:
            filters.append(Hotel.manager_id == manager_id)
        return filters

    async def search(
        self,
        *,
        params: PaginationParams,
        search: str | None = None,
        status: HotelStatus | None = None,
        sort: str | None = None,
        manager_id: uuid.UUID | None = None,
    ) -> tuple[Sequence[Hotel], int]:
        filters = self._build_filters(search=search, status=status, manager_id=manager_id)
        order_by = build_order_by(sort, SORTABLE, Hotel.created_at.desc())
        items = await self.list(
            offset=params.offset,
            limit=params.limit,
            order_by=order_by,
            filters=filters,
        )
        total = await self.count(filters=filters)
        return items, total

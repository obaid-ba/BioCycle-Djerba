"""Data access for alerts."""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select

from app.features.alerts.models import Alert, AlertSeverity, AlertStatus, AlertType
from app.features.hotels.models import Hotel
from app.shared.repository import BaseRepository
from app.shared.schemas import PaginationParams
from app.shared.sorting import build_order_by

ALERT_SORTABLE = {
    "severity": Alert.severity,
    "status": Alert.status,
    "type": Alert.type,
    "created_at": Alert.created_at,
}


class AlertRepository(BaseRepository[Alert]):
    model = Alert

    async def find_open(self, bin_id: uuid.UUID, type_: AlertType) -> Alert | None:
        stmt = select(Alert).where(
            Alert.bin_id == bin_id,
            Alert.type == type_,
            Alert.status == AlertStatus.OPEN,
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def search(
        self,
        *,
        params: PaginationParams,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        type_: AlertType | None = None,
        hotel_id: uuid.UUID | None = None,
        bin_id: uuid.UUID | None = None,
        sort: str | None = None,
        manager_id: uuid.UUID | None = None,
    ) -> tuple[Sequence[Alert], int]:
        stmt = select(Alert)
        count_stmt = select(func.count()).select_from(Alert)

        if manager_id is not None:
            # Managers see only alerts tied to their hotels (system alerts hidden).
            join_cond = Alert.hotel_id == Hotel.id
            stmt = stmt.join(Hotel, join_cond).where(Hotel.manager_id == manager_id)
            count_stmt = count_stmt.join(Hotel, join_cond).where(Hotel.manager_id == manager_id)
        if status is not None:
            stmt = stmt.where(Alert.status == status)
            count_stmt = count_stmt.where(Alert.status == status)
        if severity is not None:
            stmt = stmt.where(Alert.severity == severity)
            count_stmt = count_stmt.where(Alert.severity == severity)
        if type_ is not None:
            stmt = stmt.where(Alert.type == type_)
            count_stmt = count_stmt.where(Alert.type == type_)
        if hotel_id is not None:
            stmt = stmt.where(Alert.hotel_id == hotel_id)
            count_stmt = count_stmt.where(Alert.hotel_id == hotel_id)
        if bin_id is not None:
            stmt = stmt.where(Alert.bin_id == bin_id)
            count_stmt = count_stmt.where(Alert.bin_id == bin_id)

        order_by = build_order_by(sort, ALERT_SORTABLE, Alert.created_at.desc())
        stmt = stmt.order_by(order_by).offset(params.offset).limit(params.limit)

        items = (await self.db.execute(stmt)).scalars().all()
        total = int((await self.db.execute(count_stmt)).scalar_one())
        return items, total

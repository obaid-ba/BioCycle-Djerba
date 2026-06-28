"""Alert business logic: the auto-rules engine and the manual lifecycle."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.features.activity.service import ActivityService
from app.features.alerts.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    AlertType,
)
from app.features.alerts.repository import AlertRepository
from app.features.alerts.schemas import AlertCreate
from app.features.auth.models import User, UserRole
from app.features.bins.models import SensorReading
from app.features.bins.repository import BinRepository
from app.features.hotels.repository import HotelRepository
from app.realtime.events import build_alert_event
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.schemas import PaginationParams


class AlertService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.alerts = AlertRepository(db)
        self.bins = BinRepository(db)
        self.hotels = HotelRepository(db)
        self.activity = ActivityService(db)

    @staticmethod
    def _manager_scope(user: User) -> uuid.UUID | None:
        return user.id if user.role == UserRole.HOTEL_MANAGER else None

    async def get_or_404(self, alert_id: uuid.UUID, user: User) -> Alert:
        alert = await self.alerts.get(alert_id)
        if alert is None:
            raise NotFoundError("Alert not found")
        scope = self._manager_scope(user)
        if scope is not None:
            if alert.hotel_id is None:
                raise NotFoundError("Alert not found")
            hotel = await self.hotels.get(alert.hotel_id)
            if hotel is None or hotel.manager_id != scope:
                raise NotFoundError("Alert not found")
        return alert

    async def list(
        self,
        *,
        params: PaginationParams,
        user: User,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        type_: AlertType | None = None,
        hotel_id: uuid.UUID | None = None,
        bin_id: uuid.UUID | None = None,
        sort: str | None = None,
    ) -> tuple[Sequence[Alert], int]:
        items, total = await self.alerts.search(
            params=params,
            status=status,
            severity=severity,
            type_=type_,
            hotel_id=hotel_id,
            bin_id=bin_id,
            sort=sort,
            manager_id=self._manager_scope(user),
        )
        return items, total  # router maps to schema

    async def create(self, data: AlertCreate, user: User) -> Alert:
        if data.hotel_id is not None and await self.hotels.get(data.hotel_id) is None:
            raise ValidationError("Referenced hotel does not exist")
        if data.bin_id is not None and await self.bins.get(data.bin_id) is None:
            raise ValidationError("Referenced bin does not exist")
        alert = Alert(**data.model_dump(), status=AlertStatus.OPEN)
        alert = await self.alerts.add(alert)
        await self.activity.record(
            action="alert.created",
            user=user,
            entity_type="alert",
            entity_id=alert.id,
            message=alert.title,
        )
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def acknowledge(self, alert_id: uuid.UUID, user: User) -> Alert:
        alert = await self.get_or_404(alert_id, user)
        if alert.status == AlertStatus.RESOLVED:
            raise ValidationError("A resolved alert cannot be acknowledged")
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = user.id
        alert.acknowledged_at = datetime.now(UTC)
        await self.activity.record(
            action="alert.acknowledged",
            user=user,
            entity_type="alert",
            entity_id=alert.id,
        )
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def resolve(self, alert_id: uuid.UUID, user: User) -> Alert:
        alert = await self.get_or_404(alert_id, user)
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(UTC)
        await self.activity.record(
            action="alert.resolved",
            user=user,
            entity_type="alert",
            entity_id=alert.id,
        )
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def delete(self, alert_id: uuid.UUID, user: User) -> None:
        alert = await self.get_or_404(alert_id, user)
        await self.alerts.delete(alert)
        await self.db.commit()

    # ----------------------------- rules engine ---------------------------- #

    async def evaluate_for_reading(self, reading: SensorReading) -> Sequence[dict]:
        """Raise alerts from a new reading; return broadcast events for new ones."""
        bin_ = await self.bins.get(reading.bin_id)
        if bin_ is None:
            return []

        events: list[dict] = []

        if reading.fill_level is not None and (reading.fill_level >= settings.ALERT_FILL_THRESHOLD):
            severity = (
                AlertSeverity.CRITICAL
                if reading.fill_level >= settings.ALERT_FILL_CRITICAL
                else AlertSeverity.WARNING
            )
            event = await self._raise_if_absent(
                bin_=bin_,
                type_=AlertType.BIN_FULL,
                severity=severity,
                title=f"Bin {bin_.code} is {reading.fill_level:.0f}% full",
                context={"fill_level": reading.fill_level},
            )
            if event is not None:
                events.append(event)

        if reading.battery_level is not None and (
            reading.battery_level <= settings.ALERT_BATTERY_THRESHOLD
        ):
            event = await self._raise_if_absent(
                bin_=bin_,
                type_=AlertType.BIN_BATTERY_LOW,
                severity=AlertSeverity.WARNING,
                title=f"Bin {bin_.code} battery low ({reading.battery_level:.0f}%)",
                context={"battery_level": reading.battery_level},
            )
            if event is not None:
                events.append(event)

        return events

    async def _raise_if_absent(
        self,
        *,
        bin_,
        type_: AlertType,
        severity: AlertSeverity,
        title: str,
        context: dict,
    ) -> dict | None:
        # Dedup: skip if an OPEN alert of this type already exists for the bin.
        if await self.alerts.find_open(bin_.id, type_) is not None:
            return None
        alert = Alert(
            hotel_id=bin_.hotel_id,
            bin_id=bin_.id,
            type=type_,
            severity=severity,
            status=AlertStatus.OPEN,
            title=title,
            context=context,
        )
        await self.alerts.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        return build_alert_event(alert)

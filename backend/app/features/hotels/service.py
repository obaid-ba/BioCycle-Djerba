"""Hotel business logic: RBAC scoping, manager validation, transactions."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import User, UserRole
from app.features.auth.repository import UserRepository
from app.features.hotels.models import Hotel, HotelStatus
from app.features.hotels.repository import HotelRepository
from app.features.hotels.schemas import HotelCreate, HotelRead, HotelUpdate
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.schemas import Page, PaginationParams


class HotelService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.hotels = HotelRepository(db)
        self.users = UserRepository(db)

    @staticmethod
    def _manager_scope(user: User) -> uuid.UUID | None:
        """Hotel managers are restricted to their own hotels; staff see all."""
        return user.id if user.role == UserRole.HOTEL_MANAGER else None

    async def _validate_manager(self, manager_id: uuid.UUID | None) -> None:
        if manager_id is None:
            return
        manager = await self.users.get(manager_id)
        if manager is None:
            raise ValidationError("Assigned manager does not exist")
        if manager.role != UserRole.HOTEL_MANAGER:
            raise ValidationError("Assigned user is not a hotel manager")

    async def get_or_404(self, hotel_id: uuid.UUID, user: User) -> Hotel:
        hotel = await self.hotels.get(hotel_id)
        scope = self._manager_scope(user)
        # Scoped users get 404 (not 403) for others' hotels — don't leak existence.
        if hotel is None or (scope is not None and hotel.manager_id != scope):
            raise NotFoundError("Hotel not found")
        return hotel

    async def list(
        self,
        *,
        params: PaginationParams,
        user: User,
        search: str | None = None,
        status: HotelStatus | None = None,
        sort: str | None = None,
    ) -> Page[HotelRead]:
        items, total = await self.hotels.search(
            params=params,
            search=search,
            status=status,
            sort=sort,
            manager_id=self._manager_scope(user),
        )
        return Page.create([HotelRead.model_validate(h) for h in items], total, params)

    async def create(self, data: HotelCreate, user: User) -> Hotel:
        await self._validate_manager(data.manager_id)
        hotel = Hotel(**data.model_dump())
        hotel = await self.hotels.add(hotel)
        await self.db.commit()
        await self.db.refresh(hotel)
        return hotel

    async def update(self, hotel_id: uuid.UUID, data: HotelUpdate, user: User) -> Hotel:
        hotel = await self.get_or_404(hotel_id, user)
        changes = data.model_dump(exclude_unset=True)
        if "manager_id" in changes:
            await self._validate_manager(changes["manager_id"])
        for field, value in changes.items():
            setattr(hotel, field, value)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(hotel)
        return hotel

    async def delete(self, hotel_id: uuid.UUID, user: User) -> None:
        hotel = await self.get_or_404(hotel_id, user)
        await self.hotels.delete(hotel)
        await self.db.commit()

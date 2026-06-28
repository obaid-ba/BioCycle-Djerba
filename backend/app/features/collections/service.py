"""Waste collection business logic, including the AI prediction flow."""

import uuid
from datetime import datetime

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import User, UserRole
from app.features.bins.repository import BinRepository
from app.features.collections.models import (
    Prediction,
    PredictionStatus,
    WasteCollection,
)
from app.features.collections.repository import (
    CollectionRepository,
    PredictionRepository,
)
from app.features.collections.schemas import (
    PredictionRead,
    WasteCollectionCreate,
    WasteCollectionRead,
    WasteCollectionUpdate,
)
from app.features.hotels.repository import HotelRepository
from app.integrations.ai_service import (
    AIPredictionResponse,
    AIServiceClient,
    AIServiceError,
    PredictionRequest,
)
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.schemas import Page, PaginationParams


class CollectionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.collections = CollectionRepository(db)
        self.predictions = PredictionRepository(db)
        self.hotels = HotelRepository(db)
        self.bins = BinRepository(db)

    @staticmethod
    def _manager_scope(user: User) -> uuid.UUID | None:
        return user.id if user.role == UserRole.HOTEL_MANAGER else None

    async def _validate_refs(self, hotel_id: uuid.UUID, bin_id: uuid.UUID | None) -> None:
        if await self.hotels.get(hotel_id) is None:
            raise ValidationError("Referenced hotel does not exist")
        if bin_id is not None:
            bin_ = await self.bins.get(bin_id)
            if bin_ is None:
                raise ValidationError("Referenced bin does not exist")
            if bin_.hotel_id != hotel_id:
                raise ValidationError("Bin does not belong to the given hotel")

    async def get_or_404(self, collection_id: uuid.UUID, user: User) -> WasteCollection:
        collection = await self.collections.get(collection_id)
        if collection is None:
            raise NotFoundError("Waste collection not found")
        scope = self._manager_scope(user)
        if scope is not None:
            hotel = await self.hotels.get(collection.hotel_id)
            if hotel is None or hotel.manager_id != scope:
                raise NotFoundError("Waste collection not found")
        return collection

    async def list(
        self,
        *,
        params: PaginationParams,
        user: User,
        hotel_id: uuid.UUID | None = None,
        bin_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort: str | None = None,
    ) -> Page[WasteCollectionRead]:
        items, total = await self.collections.search(
            params=params,
            hotel_id=hotel_id,
            bin_id=bin_id,
            date_from=date_from,
            date_to=date_to,
            sort=sort,
            manager_id=self._manager_scope(user),
        )
        return Page.create([WasteCollectionRead.model_validate(c) for c in items], total, params)

    async def create(self, data: WasteCollectionCreate, user: User) -> WasteCollection:
        await self._validate_refs(data.hotel_id, data.bin_id)
        collection = WasteCollection(**data.model_dump(exclude_none=False))
        collection = await self.collections.add(collection)
        await self.db.commit()
        await self.db.refresh(collection)
        return collection

    async def update(
        self, collection_id: uuid.UUID, data: WasteCollectionUpdate, user: User
    ) -> WasteCollection:
        collection = await self.get_or_404(collection_id, user)
        changes = data.model_dump(exclude_unset=True)
        if "bin_id" in changes:
            await self._validate_refs(collection.hotel_id, changes["bin_id"])
        for field, value in changes.items():
            setattr(collection, field, value)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(collection)
        return collection

    async def delete(self, collection_id: uuid.UUID, user: User) -> None:
        collection = await self.get_or_404(collection_id, user)
        await self.collections.delete(collection)
        await self.db.commit()

    async def predict(
        self, collection_id: uuid.UUID, user: User, ai_client: AIServiceClient
    ) -> Prediction:
        collection = await self.get_or_404(collection_id, user)
        payload = PredictionRequest(
            organic_weight_kg=collection.organic_weight_kg,
            non_organic_weight_kg=collection.non_organic_weight_kg,
            total_weight_kg=collection.organic_weight_kg + collection.non_organic_weight_kg,
            hotel_id=str(collection.hotel_id),
            collected_at=collection.collected_at.isoformat(),
        ).model_dump()

        try:
            raw = await ai_client.predict(payload)
            parsed = AIPredictionResponse.model_validate(raw)
        except (AIServiceError, PydanticValidationError) as exc:
            message = (
                exc.message
                if isinstance(exc, AIServiceError)
                else "The AI service returned a malformed response."
            )
            # Persist the failed attempt for auditing, then surface the error.
            await self.predictions.add(
                Prediction(
                    collection_id=collection.id,
                    status=PredictionStatus.FAILED,
                    error_message=message,
                )
            )
            await self.db.commit()
            raise AIServiceError(message) from exc

        prediction = Prediction(
            collection_id=collection.id,
            status=PredictionStatus.SUCCESS,
            predicted_energy_kwh=parsed.energy_kwh,
            predicted_biogas_m3=parsed.biogas_m3,
            co2_saved_kg=parsed.co2_saved_kg,
            model_version=parsed.model_version,
            raw_response=raw,
        )
        prediction = await self.predictions.add(prediction)
        await self.db.commit()
        await self.db.refresh(prediction)
        return prediction

    async def list_predictions(
        self, collection_id: uuid.UUID, params: PaginationParams, user: User
    ) -> Page[PredictionRead]:
        await self.get_or_404(collection_id, user)
        items, total = await self.predictions.list_for_collection(collection_id, params)
        return Page.create([PredictionRead.model_validate(p) for p in items], total, params)

    async def latest_prediction(self, collection_id: uuid.UUID, user: User) -> Prediction:
        await self.get_or_404(collection_id, user)
        prediction = await self.predictions.latest_for_collection(collection_id)
        if prediction is None:
            raise NotFoundError("No prediction exists for this collection yet")
        return prediction

"""Collection-request business logic.

Owns the entire lifecycle: creation + AI scoring on behalf of a hotel, the
operator triage queue, and every guarded status transition. Controllers stay
thin — all rules (ownership scoping, legal transitions, required fields per
step) live here. This service is the transaction boundary (`commit`).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.features.activity.service import ActivityService
from app.features.auth.models import User, UserRole
from app.features.hotels.repository import HotelRepository
from app.features.requests.ai_stub import AIScorer, default_scorer
from app.features.requests.models import AIStatus, CollectionRequest
from app.features.requests.repository import RequestRepository
from app.features.requests.schemas import (
    CollectionRequestCreate,
    CollectionRequestRead,
    RequestDecision,
    RequestTransition,
)
from app.features.requests.state_machine import (
    RequestStatus,
    assert_transition_allowed,
)
from app.shared.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.shared.geo import haversine_km
from app.shared.schemas import Page, PaginationParams

# Transitions an operator may drive directly via the /transition endpoint.
# (PENDING -> ACCEPTED/REJECTED goes through /decision instead.)
_OPERATOR_TRANSITIONS = frozenset(
    {RequestStatus.ON_THE_WAY, RequestStatus.COLLECTED, RequestStatus.COMPLETED}
)


class RequestService:
    def __init__(self, db: AsyncSession, scorer: AIScorer = default_scorer) -> None:
        self.db = db
        self.requests = RequestRepository(db)
        self.hotels = HotelRepository(db)
        self.activity = ActivityService(db)
        self.scorer = scorer

    # ----------------------------------------------------------------- scoping
    @staticmethod
    def _hotel_scope(user: User) -> uuid.UUID | None:
        """Hotel managers see only their own requests; operators/admins see all."""
        return user.id if user.role == UserRole.HOTEL_MANAGER else None

    @staticmethod
    def _distance_to_plant(hotel) -> float | None:
        """Straight-line km from the hotel to the plant, or None if the hotel has
        no coordinates. Snapshotted onto the request so the operator queue can
        rank by proximity and show why."""
        if hotel is None or hotel.latitude is None or hotel.longitude is None:
            return None
        return round(
            haversine_km(
                hotel.latitude,
                hotel.longitude,
                settings.PLANT_LATITUDE,
                settings.PLANT_LONGITUDE,
            ),
            2,
        )

    async def _resolve_hotel_for_manager(
        self, user: User, hotel_id: uuid.UUID | None
    ) -> uuid.UUID:
        """Pick and authorize the hotel a manager is filing a request for.

        A manager may own several hotels. If they own exactly one, it's implied;
        otherwise `hotel_id` must be provided and must belong to them.
        """
        owned, total = await self.hotels.search(
            params=PaginationParams(page=1, page_size=100),
            manager_id=user.id,
        )
        if total == 0:
            raise ValidationError("You are not assigned to any hotel")

        if hotel_id is None:
            if total > 1:
                raise ValidationError(
                    "You manage multiple hotels; specify hotel_id for this request"
                )
            return owned[0].id

        if not any(h.id == hotel_id for h in owned):
            # Don't leak whether the hotel exists at all.
            raise NotFoundError("Hotel not found")
        return hotel_id

    # ------------------------------------------------------------------- reads
    async def get_or_404(self, request_id: uuid.UUID, user: User) -> CollectionRequest:
        req = await self.requests.get(request_id)
        if req is None:
            raise NotFoundError("Request not found")
        # Scoped users get 404 (not 403) for others' requests — don't leak existence.
        if self._hotel_scope(user) is not None:
            if req.hotel_id not in await self._owned_hotel_ids(user):
                raise NotFoundError("Request not found")
        return req

    async def _owned_hotel_ids(self, user: User) -> set[uuid.UUID]:
        owned, _ = await self.hotels.search(
            params=PaginationParams(page=1, page_size=100),
            manager_id=user.id,
        )
        return {h.id for h in owned}

    async def list(
        self,
        *,
        params: PaginationParams,
        user: User,
        status: RequestStatus | None = None,
        hotel_id: uuid.UUID | None = None,
    ) -> Page[CollectionRequestRead]:
        """Operator queue / hotel history — ordered by AI priority (desc)."""
        # Hotel managers are hard-scoped to their own hotels regardless of the
        # hotel_id filter they pass.
        if self._hotel_scope(user) is not None:
            owned = await self._owned_hotel_ids(user)
            if hotel_id is not None and hotel_id not in owned:
                raise NotFoundError("Hotel not found")
            # If they own exactly one hotel, scope to it; the multi-hotel case
            # without an explicit filter still needs per-row filtering, handled
            # by restricting hotel_id below.
            if hotel_id is None and len(owned) == 1:
                hotel_id = next(iter(owned))

        items, total = await self.requests.search(
            params=params, status=status, hotel_id=hotel_id
        )
        # Defense in depth: for a multi-hotel manager with no filter, drop rows
        # outside their ownership set.
        if self._hotel_scope(user) is not None and hotel_id is None:
            owned = await self._owned_hotel_ids(user)
            items = [r for r in items if r.hotel_id in owned]
        return Page.create(
            [CollectionRequestRead.model_validate(r) for r in items], total, params
        )

    # ----------------------------------------------------------------- create
    async def create(
        self,
        data: CollectionRequestCreate,
        user: User,
        hotel_id: uuid.UUID | None = None,
    ) -> CollectionRequest:
        target_hotel_id = await self._resolve_hotel_for_manager(user, hotel_id)
        hotel = await self.hotels.get(target_hotel_id)

        req = CollectionRequest(
            hotel_id=target_hotel_id,
            declared_weight_kg=data.declared_weight_kg,
            status=RequestStatus.PENDING,
            ai_status=AIStatus.PENDING,
            distance_to_plant_km=self._distance_to_plant(hotel),
        )
        req = await self.requests.add(req)

        # Score synchronously via the (stub) scorer so the operator queue has a
        # priority immediately. When the real HTTP AI is wired, this call moves
        # to a background task and the request stays PENDING/ai_status=pending
        # until the result arrives.
        await self._apply_ai_scoring(req)

        await self.activity.record(
            action="request.created",
            user=user,
            entity_type="collection_request",
            entity_id=req.id,
            message=f"{req.declared_weight_kg} kg",
        )
        await self.db.commit()
        await self.db.refresh(req)
        return req

    async def _apply_ai_scoring(self, req: CollectionRequest) -> None:
        """Populate AI fields from the scorer; never fail request creation on AI."""
        try:
            result = await self.scorer.score(
                request_id=req.id, declared_weight_kg=req.declared_weight_kg
            )
        except Exception as exc:  # noqa: BLE001 — AI failure must not 500 the create
            req.ai_status = AIStatus.FAILED
            req.ai_error = str(exc)[:500]
            req.status = RequestStatus.AI_FAILED
            await self.db.flush()
            return

        req.ai_status = AIStatus.SUCCESS
        req.ai_quality_score = result.quality_score
        req.ai_organic_purity = result.organic_purity
        req.ai_contamination = result.contamination
        req.ai_estimated_methane_m3 = result.estimated_methane_m3
        req.ai_estimated_energy_kwh = result.estimated_energy_kwh
        req.ai_estimated_co2_kg = result.estimated_co2_kg
        req.ai_priority_score = result.priority_score
        req.ai_confidence = result.confidence
        req.ai_model_version = result.model_version
        req.ai_error = None
        await self.db.flush()

    # --------------------------------------------------------------- decisions
    async def decide(
        self, request_id: uuid.UUID, data: RequestDecision, operator: User
    ) -> CollectionRequest:
        """Operator accepts or rejects a request awaiting a decision."""
        req = await self.get_or_404(request_id, operator)
        target = RequestStatus.ACCEPTED if data.accept else RequestStatus.REJECTED
        assert_transition_allowed(req.status, target)

        if not data.accept and not (data.rejection_reason and data.rejection_reason.strip()):
            raise ValidationError("A rejection reason is required when rejecting a request")

        req.status = target
        req.decided_by = operator.id
        req.decided_at = datetime.now(timezone.utc)
        req.rejection_reason = data.rejection_reason if not data.accept else None
        if data.notes:
            req.operator_notes = data.notes

        await self.db.flush()
        await self.activity.record(
            action=f"request.{target.value}",
            user=operator,
            entity_type="collection_request",
            entity_id=req.id,
            message=req.rejection_reason,
        )
        await self.db.commit()
        await self.db.refresh(req)
        return req

    async def transition(
        self, request_id: uuid.UUID, data: RequestTransition, operator: User
    ) -> CollectionRequest:
        """Drive an accepted request forward: on_the_way -> collected -> completed."""
        req = await self.get_or_404(request_id, operator)

        if data.target not in _OPERATOR_TRANSITIONS:
            raise ValidationError(
                "Use the decision endpoint for accept/reject; "
                "this endpoint only advances an accepted request"
            )
        assert_transition_allowed(req.status, data.target)

        if data.target == RequestStatus.COLLECTED:
            if data.collected_weight_kg is None:
                raise ValidationError(
                    "collected_weight_kg is required when marking a request collected"
                )
            req.collected_weight_kg = data.collected_weight_kg

        if data.target == RequestStatus.COMPLETED:
            req.completed_at = datetime.now(timezone.utc)

        req.status = data.target
        if data.notes:
            req.operator_notes = data.notes

        await self.db.flush()
        await self.activity.record(
            action=f"request.{data.target.value}",
            user=operator,
            entity_type="collection_request",
            entity_id=req.id,
        )
        await self.db.commit()
        await self.db.refresh(req)
        return req

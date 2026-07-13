"""Data access for collection requests, including the operator-queue ordering."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.sql import ColumnExpressionArgument

from app.features.requests.models import CollectionRequest
from app.features.requests.state_machine import RequestStatus
from app.shared.repository import BaseRepository
from app.shared.schemas import PaginationParams


class RequestRepository(BaseRepository[CollectionRequest]):
    model = CollectionRequest

    @staticmethod
    def _build_filters(
        *,
        status: RequestStatus | None,
        hotel_id: uuid.UUID | None,
    ) -> list[ColumnExpressionArgument[bool]]:
        filters: list[ColumnExpressionArgument[bool]] = []
        if status is not None:
            filters.append(CollectionRequest.status == status)
        if hotel_id is not None:
            filters.append(CollectionRequest.hotel_id == hotel_id)
        return filters

    async def search(
        self,
        *,
        params: PaginationParams,
        status: RequestStatus | None = None,
        hotel_id: uuid.UUID | None = None,
    ) -> tuple[Sequence[CollectionRequest], int]:
        """List requests ordered as the operator queue, by an EXPLAINABLE rule.

        Ordering (deliberately not the opaque AI priority score, so an operator
        can see *why* a request tops the queue):
          1. ai_quality_score DESC, NULLS LAST — best-quality feedstock first;
             un-scored requests never jump ahead.
          2. distance_to_plant_km ASC, NULLS LAST — tiebreak on proximity to the
             plant (shorter haul first); requests with no known distance last.
          3. created_at DESC — final, deterministic tiebreak (newest first).
        """
        filters = self._build_filters(status=status, hotel_id=hotel_id)

        # Multi-key ordering can't go through BaseRepository.list() (single
        # order_by); build the statement here. count() is still shared.
        stmt = select(CollectionRequest)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.order_by(
            CollectionRequest.ai_quality_score.desc().nulls_last(),
            CollectionRequest.distance_to_plant_km.asc().nulls_last(),
            CollectionRequest.created_at.desc(),
        )
        stmt = stmt.offset(params.offset).limit(params.limit)
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        total = await self.count(filters=filters)
        return items, total

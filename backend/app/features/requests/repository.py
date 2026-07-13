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
        """List requests ordered as the operator queue: highest AI priority first.

        Un-scored requests (NULL priority) sort last so they never jump the queue,
        with newest-first as the tiebreaker.
        """
        filters = self._build_filters(status=status, hotel_id=hotel_id)

        # Two-key ordering (priority desc NULLS LAST, then newest) can't go
        # through BaseRepository.list(), which takes a single order_by; build the
        # statement here. count() is still shared.
        stmt = select(CollectionRequest)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.order_by(
            CollectionRequest.ai_priority_score.desc().nulls_last(),
            CollectionRequest.created_at.desc(),
        )
        stmt = stmt.offset(params.offset).limit(params.limit)
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        total = await self.count(filters=filters)
        return items, total

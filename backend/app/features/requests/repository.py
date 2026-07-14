"""Data access for collection requests, including the operator-queue ordering."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.sql import ColumnExpressionArgument

from app.features.requests.models import CollectionRequest
from app.features.requests.state_machine import TERMINAL_STATES, RequestStatus
from app.shared.repository import BaseRepository
from app.shared.schemas import PaginationParams


class RequestRepository(BaseRepository[CollectionRequest]):
    model = CollectionRequest

    @staticmethod
    def _build_filters(
        *,
        status: RequestStatus | None,
        hotel_id: uuid.UUID | None,
        terminal: bool | None = None,
    ) -> list[ColumnExpressionArgument[bool]]:
        filters: list[ColumnExpressionArgument[bool]] = []
        if status is not None:
            filters.append(CollectionRequest.status == status)
        if hotel_id is not None:
            filters.append(CollectionRequest.hotel_id == hotel_id)
        if terminal is not None:
            # terminal=True  -> finished requests (completed/rejected)  [History]
            # terminal=False -> active requests still in progress       [Requests]
            terminal_values = list(TERMINAL_STATES)
            if terminal:
                filters.append(CollectionRequest.status.in_(terminal_values))
            else:
                filters.append(CollectionRequest.status.notin_(terminal_values))
        return filters

    async def search(
        self,
        *,
        params: PaginationParams,
        status: RequestStatus | None = None,
        hotel_id: uuid.UUID | None = None,
        terminal: bool | None = None,
    ) -> tuple[Sequence[CollectionRequest], int]:
        """List requests ordered as the operator queue, by the business rules.

        AI provides the ranking; the operator always has the final decision. The
        five ordering keys, in priority order:
          1. ai_priority_score  DESC, NULLS LAST — the AI's recommended order.
          2. ai_quality_score   DESC, NULLS LAST — better feedstock next.
          3. distance_to_plant_km ASC, NULLS LAST — shorter haul to the plant.
          4. declared_weight_kg DESC — larger loads first.
          5. created_at         ASC  — oldest first (FIFO), deterministic.

        NULLS LAST on the AI keys keeps not-yet-analyzed requests (no Firebase
        result yet) from jumping the queue; the non-AI keys still order them.
        """
        filters = self._build_filters(
            status=status, hotel_id=hotel_id, terminal=terminal
        )

        # Multi-key ordering can't go through BaseRepository.list() (single
        # order_by); build the statement here. count() is still shared.
        stmt = select(CollectionRequest)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.order_by(
            CollectionRequest.ai_priority_score.desc().nulls_last(),
            CollectionRequest.ai_quality_score.desc().nulls_last(),
            CollectionRequest.distance_to_plant_km.asc().nulls_last(),
            CollectionRequest.declared_weight_kg.desc(),
            CollectionRequest.created_at.asc(),
        )
        stmt = stmt.offset(params.offset).limit(params.limit)
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        total = await self.count(filters=filters)
        return items, total

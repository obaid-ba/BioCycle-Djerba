"""Generic async repository.

Encapsulates the data-access mechanics every feature shares (fetch, list,
count, add, delete) so feature repositories only add domain-specific queries.
Repositories never commit — they `flush()` to surface DB-generated values; the
owning service decides the transaction boundary via `db.commit()`.
"""

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnExpressionArgument

from app.shared.models import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Base class for feature repositories. Subclasses set `model`."""

    model: type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return await self.db.get(self.model, entity_id)

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        order_by: ColumnExpressionArgument[Any] | None = None,
        filters: Sequence[ColumnExpressionArgument[bool]] = (),
    ) -> Sequence[ModelT]:
        stmt = select(self.model)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.order_by(order_by if order_by is not None else self.model.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count(self, filters: Sequence[ColumnExpressionArgument[bool]] = ()) -> int:
        stmt = select(func.count()).select_from(self.model)
        if filters:
            stmt = stmt.where(*filters)
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def add(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.db.delete(entity)
        await self.db.flush()

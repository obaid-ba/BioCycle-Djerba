"""Reusable Pydantic schema primitives shared across features.

`BaseSchema` enables ORM-mode (`from_attributes`) so we can return SQLAlchemy
models directly. `PaginationParams` and `Page` give every list endpoint a
consistent, typed pagination contract.
"""

from collections.abc import Sequence
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    """Injectable query params for paginated list endpoints."""

    page: int = Field(default=1, ge=1, description="1-based page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def pagination_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginationParams:
    """FastAPI dependency that builds validated PaginationParams from query."""
    return PaginationParams(page=page, page_size=page_size)


class Page(BaseSchema, Generic[T]):
    """Standard paginated envelope returned by every list endpoint."""

    items: Sequence[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(cls, items: Sequence[T], total: int, params: PaginationParams) -> "Page[T]":
        pages = (total + params.page_size - 1) // params.page_size if total else 0
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=pages,
        )

"""Safe, reusable sort-string parser for list endpoints.

Accepts a `?sort=field` or `?sort=-field` (descending) string and maps it to a
SQLAlchemy ORDER BY clause — but only against an explicit allow-list of columns.
This keeps sorting flexible for clients while preventing arbitrary-column access.
"""

from typing import Any

from sqlalchemy import asc, desc
from sqlalchemy.sql import ColumnExpressionArgument

from app.shared.exceptions import ValidationError


def build_order_by(
    sort: str | None,
    allowed: dict[str, ColumnExpressionArgument[Any]],
    default: ColumnExpressionArgument[Any],
) -> ColumnExpressionArgument[Any]:
    if not sort:
        return default

    descending = sort.startswith("-")
    field = sort[1:] if descending else sort

    column = allowed.get(field)
    if column is None:
        raise ValidationError(f"Cannot sort by '{field}'. Allowed: {', '.join(sorted(allowed))}.")
    return desc(column) if descending else asc(column)

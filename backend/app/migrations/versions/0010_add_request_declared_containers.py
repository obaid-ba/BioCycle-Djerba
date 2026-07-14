"""add declared_containers to collection_requests

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-14

Hotels now declare a number of standard containers; declared_weight_kg is
derived (containers * CONTAINER_WEIGHT_KG). Backfills existing rows from their
weight using the default 700 kg/container.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_CONTAINER_KG = 700


def upgrade() -> None:
    # Add nullable first so existing rows don't violate NOT NULL.
    op.add_column(
        "collection_requests",
        sa.Column("declared_containers", sa.Integer(), nullable=True),
    )
    # Backfill: derive a container count from the stored weight (round to nearest,
    # min 1) so historical rows have a sensible value.
    op.execute(
        "UPDATE collection_requests "
        f"SET declared_containers = GREATEST(1, ROUND(declared_weight_kg / {_DEFAULT_CONTAINER_KG}))"
    )
    op.alter_column("collection_requests", "declared_containers", nullable=False)


def downgrade() -> None:
    op.drop_column("collection_requests", "declared_containers")

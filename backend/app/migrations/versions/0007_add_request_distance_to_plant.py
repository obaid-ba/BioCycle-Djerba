"""add distance_to_plant_km to collection_requests

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "collection_requests",
        sa.Column("distance_to_plant_km", sa.Float(), nullable=True),
    )
    op.create_index(
        "ix_collection_requests_distance_to_plant_km",
        "collection_requests",
        ["distance_to_plant_km"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_collection_requests_distance_to_plant_km",
        table_name="collection_requests",
    )
    op.drop_column("collection_requests", "distance_to_plant_km")

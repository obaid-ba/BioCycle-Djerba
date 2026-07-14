"""drop number_of_rooms from hotels

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-14

Removed because the field was stored/displayed but never used by any business
logic (requests, priority, analytics, reports).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("hotels", "number_of_rooms")


def downgrade() -> None:
    op.add_column(
        "hotels",
        sa.Column("number_of_rooms", sa.Integer(), nullable=True),
    )

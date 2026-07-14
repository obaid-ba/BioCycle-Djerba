"""add firebase_device_id to hotels

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-14

Links a hotel to its Firebase camera/device feed so requests for that hotel can
be analyzed from the device's detections.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "hotels",
        sa.Column("firebase_device_id", sa.String(length=120), nullable=True),
    )
    op.create_index(
        "ix_hotels_firebase_device_id",
        "hotels",
        ["firebase_device_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_hotels_firebase_device_id", table_name="hotels")
    op.drop_column("hotels", "firebase_device_id")

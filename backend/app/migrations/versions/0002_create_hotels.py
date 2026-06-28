"""create hotels table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

hotel_status = postgresql.ENUM(
    "active", "inactive", "onboarding", name="hotel_status", create_type=False
)


def upgrade() -> None:
    hotel_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "hotels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column(
            "country",
            sa.String(length=120),
            server_default="Tunisia",
            nullable=False,
        ),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("number_of_rooms", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            hotel_status,
            server_default="onboarding",
            nullable=False,
        ),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["manager_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hotels_name", "hotels", ["name"])
    op.create_index("ix_hotels_city", "hotels", ["city"])
    op.create_index("ix_hotels_status", "hotels", ["status"])
    op.create_index("ix_hotels_manager_id", "hotels", ["manager_id"])


def downgrade() -> None:
    op.drop_index("ix_hotels_manager_id", table_name="hotels")
    op.drop_index("ix_hotels_status", table_name="hotels")
    op.drop_index("ix_hotels_city", table_name="hotels")
    op.drop_index("ix_hotels_name", table_name="hotels")
    op.drop_table("hotels")
    hotel_status.drop(op.get_bind(), checkfirst=True)

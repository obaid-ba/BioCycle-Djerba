"""create smart_bins and sensor_readings tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

bin_type = postgresql.ENUM("organic", "non_organic", "mixed", name="bin_type", create_type=False)
bin_status = postgresql.ENUM(
    "online", "offline", "maintenance", name="bin_status", create_type=False
)


def upgrade() -> None:
    bin_type.create(op.get_bind(), checkfirst=True)
    bin_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "smart_bins",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("hotel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bin_type", bin_type, server_default="mixed", nullable=False),
        sa.Column("status", bin_status, server_default="offline", nullable=False),
        sa.Column("capacity_liters", sa.Float(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("fill_level", sa.Float(), nullable=True),
        sa.Column("battery_level", sa.Float(), nullable=True),
        sa.Column("last_reading_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["hotel_id"], ["hotels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_smart_bins_code", "smart_bins", ["code"], unique=True)
    op.create_index("ix_smart_bins_hotel_id", "smart_bins", ["hotel_id"])
    op.create_index("ix_smart_bins_status", "smart_bins", ["status"])

    op.create_table(
        "sensor_readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fill_level", sa.Float(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("humidity", sa.Float(), nullable=True),
        sa.Column("battery_level", sa.Float(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(["bin_id"], ["smart_bins.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sensor_readings_bin_id", "sensor_readings", ["bin_id"])
    op.create_index("ix_sensor_readings_recorded_at", "sensor_readings", ["recorded_at"])
    op.create_index(
        "ix_sensor_readings_bin_recorded",
        "sensor_readings",
        ["bin_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_sensor_readings_bin_recorded", table_name="sensor_readings")
    op.drop_index("ix_sensor_readings_recorded_at", table_name="sensor_readings")
    op.drop_index("ix_sensor_readings_bin_id", table_name="sensor_readings")
    op.drop_table("sensor_readings")

    op.drop_index("ix_smart_bins_status", table_name="smart_bins")
    op.drop_index("ix_smart_bins_hotel_id", table_name="smart_bins")
    op.drop_index("ix_smart_bins_code", table_name="smart_bins")
    op.drop_table("smart_bins")

    bin_status.drop(op.get_bind(), checkfirst=True)
    bin_type.drop(op.get_bind(), checkfirst=True)

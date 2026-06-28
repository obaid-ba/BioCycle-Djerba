"""create waste_collections and predictions tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

prediction_status = postgresql.ENUM(
    "success", "failed", name="prediction_status", create_type=False
)


def upgrade() -> None:
    prediction_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "waste_collections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hotel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("organic_weight_kg", sa.Float(), server_default="0", nullable=False),
        sa.Column("non_organic_weight_kg", sa.Float(), server_default="0", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["bin_id"], ["smart_bins.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_waste_collections_hotel_id", "waste_collections", ["hotel_id"])
    op.create_index("ix_waste_collections_bin_id", "waste_collections", ["bin_id"])
    op.create_index("ix_waste_collections_collected_at", "waste_collections", ["collected_at"])

    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("collection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", prediction_status, nullable=False),
        sa.Column("predicted_energy_kwh", sa.Float(), nullable=True),
        sa.Column("predicted_biogas_m3", sa.Float(), nullable=True),
        sa.Column("co2_saved_kg", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("raw_response", postgresql.JSONB(), nullable=True),
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
        sa.ForeignKeyConstraint(["collection_id"], ["waste_collections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predictions_collection_id", "predictions", ["collection_id"])


def downgrade() -> None:
    op.drop_index("ix_predictions_collection_id", table_name="predictions")
    op.drop_table("predictions")

    op.drop_index("ix_waste_collections_collected_at", table_name="waste_collections")
    op.drop_index("ix_waste_collections_bin_id", table_name="waste_collections")
    op.drop_index("ix_waste_collections_hotel_id", table_name="waste_collections")
    op.drop_table("waste_collections")

    prediction_status.drop(op.get_bind(), checkfirst=True)

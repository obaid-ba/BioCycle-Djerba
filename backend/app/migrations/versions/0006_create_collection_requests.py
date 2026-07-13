"""create collection_requests and request_photos tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

request_status = postgresql.ENUM(
    "pending",
    "ai_failed",
    "accepted",
    "rejected",
    "on_the_way",
    "collected",
    "completed",
    name="request_status",
    create_type=False,
)
ai_status = postgresql.ENUM(
    "pending", "success", "failed", name="ai_status", create_type=False
)


def upgrade() -> None:
    request_status.create(op.get_bind(), checkfirst=True)
    ai_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "collection_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hotel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", request_status, server_default="pending", nullable=False),
        sa.Column("declared_weight_kg", sa.Float(), nullable=False),
        sa.Column("collected_weight_kg", sa.Float(), nullable=True),
        sa.Column("ai_status", ai_status, server_default="pending", nullable=False),
        sa.Column("ai_quality_score", sa.Float(), nullable=True),
        sa.Column("ai_organic_purity", sa.Float(), nullable=True),
        sa.Column("ai_contamination", sa.Float(), nullable=True),
        sa.Column("ai_estimated_methane_m3", sa.Float(), nullable=True),
        sa.Column("ai_estimated_energy_kwh", sa.Float(), nullable=True),
        sa.Column("ai_estimated_co2_kg", sa.Float(), nullable=True),
        sa.Column("ai_priority_score", sa.Float(), nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("ai_model_version", sa.String(length=64), nullable=True),
        sa.Column("ai_error", sa.String(length=500), nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.Column("operator_notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_collection_requests_hotel_id", "collection_requests", ["hotel_id"]
    )
    op.create_index(
        "ix_collection_requests_status", "collection_requests", ["status"]
    )
    op.create_index(
        "ix_collection_requests_ai_status", "collection_requests", ["ai_status"]
    )
    op.create_index(
        "ix_collection_requests_ai_priority_score",
        "collection_requests",
        ["ai_priority_score"],
    )
    op.create_index(
        "ix_collection_requests_decided_by", "collection_requests", ["decided_by"]
    )

    op.create_table(
        "request_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["request_id"], ["collection_requests.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_request_photos_request_id", "request_photos", ["request_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_request_photos_request_id", table_name="request_photos")
    op.drop_table("request_photos")

    op.drop_index(
        "ix_collection_requests_decided_by", table_name="collection_requests"
    )
    op.drop_index(
        "ix_collection_requests_ai_priority_score", table_name="collection_requests"
    )
    op.drop_index(
        "ix_collection_requests_ai_status", table_name="collection_requests"
    )
    op.drop_index("ix_collection_requests_status", table_name="collection_requests")
    op.drop_index(
        "ix_collection_requests_hotel_id", table_name="collection_requests"
    )
    op.drop_table("collection_requests")

    ai_status.drop(op.get_bind(), checkfirst=True)
    request_status.drop(op.get_bind(), checkfirst=True)

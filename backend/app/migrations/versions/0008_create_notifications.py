"""create notifications table

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

notification_type = postgresql.ENUM(
    "request_accepted",
    "request_rejected",
    "request_completed",
    name="notification_type",
    create_type=False,
)


def upgrade() -> None:
    notification_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "is_read", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["request_id"], ["collection_requests.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_request_id", "notifications", ["request_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])


def downgrade() -> None:
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_request_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    notification_type.drop(op.get_bind(), checkfirst=True)

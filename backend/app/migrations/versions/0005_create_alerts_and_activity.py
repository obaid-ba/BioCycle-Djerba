"""create alerts and activity_logs tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

alert_type = postgresql.ENUM(
    "bin_full",
    "bin_battery_low",
    "bin_offline",
    "system",
    "custom",
    name="alert_type",
    create_type=False,
)
alert_severity = postgresql.ENUM(
    "info", "warning", "critical", name="alert_severity", create_type=False
)
alert_status = postgresql.ENUM(
    "open", "acknowledged", "resolved", name="alert_status", create_type=False
)


def upgrade() -> None:
    alert_type.create(op.get_bind(), checkfirst=True)
    alert_severity.create(op.get_bind(), checkfirst=True)
    alert_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hotel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", alert_type, nullable=False),
        sa.Column("severity", alert_severity, nullable=False),
        sa.Column("status", alert_status, server_default="open", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("context", postgresql.JSONB(), nullable=True),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["acknowledged_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_hotel_id", "alerts", ["hotel_id"])
    op.create_index("ix_alerts_bin_id", "alerts", ["bin_id"])
    op.create_index("ix_alerts_type", "alerts", ["type"])
    op.create_index("ix_alerts_status", "alerts", ["status"])

    op.create_table(
        "activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("context", postgresql.JSONB(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"])
    op.create_index("ix_activity_logs_action", "activity_logs", ["action"])


def downgrade() -> None:
    op.drop_index("ix_activity_logs_action", table_name="activity_logs")
    op.drop_index("ix_activity_logs_user_id", table_name="activity_logs")
    op.drop_table("activity_logs")

    op.drop_index("ix_alerts_status", table_name="alerts")
    op.drop_index("ix_alerts_type", table_name="alerts")
    op.drop_index("ix_alerts_bin_id", table_name="alerts")
    op.drop_index("ix_alerts_hotel_id", table_name="alerts")
    op.drop_table("alerts")

    alert_status.drop(op.get_bind(), checkfirst=True)
    alert_severity.drop(op.get_bind(), checkfirst=True)
    alert_type.drop(op.get_bind(), checkfirst=True)

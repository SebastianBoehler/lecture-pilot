"""Track provider attempt lineage, including failed requests.

Revision ID: 20260715_0009
Revises: 20260715_0008
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260715_0009"
down_revision: str | None = "20260715_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "model_usage_events",
        sa.Column("request_id", sa.String(length=32), nullable=False, server_default="legacy"),
    )
    op.add_column(
        "model_usage_events",
        sa.Column("operation_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "model_usage_events",
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "model_usage_events",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="succeeded"),
    )
    op.add_column(
        "model_usage_events",
        sa.Column("error_type", sa.String(length=80), nullable=True),
    )
    op.alter_column("model_usage_events", "request_id", server_default=None)
    op.alter_column("model_usage_events", "attempt", server_default=None)
    op.alter_column("model_usage_events", "status", server_default=None)
    op.create_index(
        "ix_model_usage_request_attempt",
        "model_usage_events",
        ["request_id", "attempt"],
    )


def downgrade() -> None:
    op.drop_index("ix_model_usage_request_attempt", table_name="model_usage_events")
    op.drop_column("model_usage_events", "error_type")
    op.drop_column("model_usage_events", "status")
    op.drop_column("model_usage_events", "attempt")
    op.drop_column("model_usage_events", "operation_id")
    op.drop_column("model_usage_events", "request_id")

"""Remove platform professor approval state.

Revision ID: 20260713_0005
Revises: 20260711_0004
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260713_0005"
down_revision: str | None = "20260711_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("professor_requests")
    op.drop_column("tenant_memberships", "professor_status")


def downgrade() -> None:
    op.add_column(
        "tenant_memberships",
        sa.Column(
            "professor_status",
            sa.String(length=24),
            nullable=False,
            server_default="not_requested",
        ),
    )
    op.create_table(
        "professor_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    op.create_index("ix_professor_requests_user_id", "professor_requests", ["user_id"])
    op.create_index(
        "uq_pending_professor_request",
        "professor_requests",
        ["user_id", "tenant_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )

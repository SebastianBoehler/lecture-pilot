"""Track asynchronous university course synchronization.

Revision ID: 20260713_0006
Revises: 20260713_0005
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260713_0006"
down_revision: str | None = "20260713_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "external_identities",
        sa.Column("course_sync_id", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "external_identities",
        sa.Column(
            "course_sync_status",
            sa.String(length=20),
            nullable=False,
            server_default="ready",
        ),
    )
    op.alter_column("external_identities", "course_sync_status", server_default=None)


def downgrade() -> None:
    op.drop_column("external_identities", "course_sync_status")
    op.drop_column("external_identities", "course_sync_id")

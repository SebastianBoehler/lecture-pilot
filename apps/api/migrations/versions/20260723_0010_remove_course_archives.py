"""Replace hidden course archives with real deletion.

Revision ID: 20260723_0010
Revises: 20260715_0009
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260723_0010"
down_revision: str | None = "20260715_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM usage_counters
        WHERE course_id IN (
            SELECT id::text FROM courses WHERE archived_at IS NOT NULL
        )
        """
    )
    op.execute("DELETE FROM courses WHERE archived_at IS NOT NULL")
    op.drop_column("courses", "archived_at")


def downgrade() -> None:
    op.add_column(
        "courses",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )

"""Enable normalized PostgreSQL query statistics.

Revision ID: 20260715_0008
Revises: 20260713_0007
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260715_0008"
down_revision: str | None = "20260713_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")


def downgrade() -> None:
    # Query statistics may predate this release and are safe to retain on rollback.
    pass

"""Drop university course-sync state; no login path synchronizes Alma or ILIAS any more."""

from alembic import op
import sqlalchemy as sa

revision = "20261015_0013"
down_revision = "20261015_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("external_identities", "course_sync_status")
    op.drop_column("external_identities", "course_sync_id")
    op.execute(
        "UPDATE external_identities "
        "SET provider_claims = (provider_claims::jsonb - 'course_sync_sources')::json"
    )


def downgrade() -> None:
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

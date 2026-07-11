"""Persist server-verified external identity claims."""

from alembic import op
import sqlalchemy as sa


revision = "20260711_0004"
down_revision = "20260710_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("local_credentials")
    op.add_column(
        "external_identities",
        sa.Column(
            "provider_claims",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.alter_column("external_identities", "provider_claims", server_default=None)


def downgrade() -> None:
    op.drop_column("external_identities", "provider_claims")
    op.create_table(
        "local_credentials",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

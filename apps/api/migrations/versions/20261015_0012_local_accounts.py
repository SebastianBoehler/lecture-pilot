"""Independent verified email accounts; end sessions created before this change."""

from alembic import op
import sqlalchemy as sa

revision = "20261015_0012"
down_revision = "20261012_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "local_credentials",
        sa.Column("email", sa.String(200), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("password_hash", sa.String(300), nullable=False),
    )
    op.create_table(
        "account_tokens",
        sa.Column("email", sa.String(200), primary_key=True),
        sa.Column("purpose", sa.String(20), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(300)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute("UPDATE sessions SET revoked_at = CURRENT_TIMESTAMP WHERE revoked_at IS NULL")


def downgrade() -> None:
    op.drop_table("account_tokens")
    op.drop_table("local_credentials")

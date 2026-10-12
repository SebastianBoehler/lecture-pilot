"""Store learner requests for LecturePilot support of observed university courses.

Revision ID: 20261012_0011
Revises: 20260723_0010
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261012_0011"
down_revision: str | None = "20260723_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "course_support_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.Column("external_course_id", sa.String(length=240), nullable=False),
        sa.Column("term", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "source", "external_course_id", "term", name="uq_user_course_support"
        ),
    )
    op.create_index(
        "ix_course_support_course",
        "course_support_requests",
        ["source", "external_course_id", "term"],
    )


def downgrade() -> None:
    op.drop_index("ix_course_support_course", table_name="course_support_requests")
    op.drop_table("course_support_requests")

"""Add database-backed identity, sessions, courses, enrollments, and audit records."""

from alembic import op
import sqlalchemy as sa


revision = "20260710_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("display_name", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "external_identities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "subject", name="uq_external_identity"),
    )
    op.create_index("ix_external_identities_user_id", "external_identities", ["user_id"])
    op.create_table(
        "tenant_memberships",
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("tenant_id", sa.String(120), primary_key=True),
        sa.Column("professor_status", sa.String(24), nullable=False),
        sa.Column("platform_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "professor_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("tenant_id", sa.String(120), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
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
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("tenant_id", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_table(
        "external_course_observations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("external_course_id", sa.String(240), nullable=False),
        sa.Column("term", sa.String(80), nullable=False),
        sa.Column("number", sa.String(80)),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("organization", sa.String(200)),
        sa.Column("instructor", sa.String(200)),
        sa.Column("display_url", sa.String(700)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id",
            "source",
            "external_course_id",
            "term",
            name="uq_user_external_course_observation",
        ),
    )
    op.create_index(
        "ix_external_course_observations_user_id", "external_course_observations", ["user_id"]
    )
    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(120), nullable=False),
        sa.Column(
            "owner_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("term", sa.String(80), nullable=False),
        sa.Column("access_policy", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_courses_tenant_id", "courses", ["tenant_id"])
    op.create_index("ix_courses_tenant_owner", "courses", ["tenant_id", "owner_user_id"])
    op.create_table(
        "course_external_refs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "course_id", sa.Uuid(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("tenant_id", sa.String(120), nullable=False),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("external_course_id", sa.String(240), nullable=False),
        sa.Column("term", sa.String(80), nullable=False),
        sa.Column("number", sa.String(80)),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("organization", sa.String(200)),
        sa.Column("instructor", sa.String(200)),
        sa.Column("display_url", sa.String(700)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "source", "external_course_id", "term", name="uq_external_course_term"
        ),
    )
    op.create_index("ix_course_external_refs_course_id", "course_external_refs", ["course_id"])
    op.create_table(
        "course_enrollments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "course_id", sa.Uuid(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("external_course_id", sa.String(240), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "course_id",
            "user_id",
            "source",
            "external_course_id",
            name="uq_course_enrollment_evidence",
        ),
    )
    op.create_index(
        "ix_active_course_enrollment", "course_enrollments", ["course_id", "user_id", "status"]
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(120), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(80)),
        sa.Column("target_id", sa.String(240)),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_tenant_created", "audit_events", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("course_enrollments")
    op.drop_table("course_external_refs")
    op.drop_table("courses")
    op.drop_table("external_course_observations")
    op.drop_table("sessions")
    op.drop_table("professor_requests")
    op.drop_table("tenant_memberships")
    op.drop_table("external_identities")
    op.drop_table("users")

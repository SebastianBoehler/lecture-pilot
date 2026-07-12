from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Integer,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    display_name: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ExternalIdentityRecord(Base):
    __tablename__ = "external_identities"
    __table_args__ = (UniqueConstraint("provider", "subject", name="uq_external_identity"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    provider_claims: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TenantMembershipRecord(Base):
    __tablename__ = "tenant_memberships"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    tenant_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    platform_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExternalCourseObservationRecord(Base):
    __tablename__ = "external_course_observations"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source",
            "external_course_id",
            "term",
            name="uq_user_external_course_observation",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    external_course_id: Mapped[str] = mapped_column(String(240), nullable=False)
    term: Mapped[str] = mapped_column(String(80), nullable=False)
    number: Mapped[str | None] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(200))
    instructor: Mapped[str | None] = mapped_column(String(200))
    display_url: Mapped[str | None] = mapped_column(String(700))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CourseRecord(Base):
    __tablename__ = "courses"
    __table_args__ = (Index("ix_courses_tenant_owner", "tenant_id", "owner_user_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    term: Mapped[str] = mapped_column(String(80), nullable=False)
    access_policy: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CourseExternalRefRecord(Base):
    __tablename__ = "course_external_refs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source",
            "external_course_id",
            "term",
            name="uq_external_course_term",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False)
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    external_course_id: Mapped[str] = mapped_column(String(240), nullable=False)
    term: Mapped[str] = mapped_column(String(80), nullable=False)
    number: Mapped[str | None] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(200))
    instructor: Mapped[str | None] = mapped_column(String(200))
    display_url: Mapped[str | None] = mapped_column(String(700))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CourseEnrollmentRecord(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "user_id",
            "source",
            "external_course_id",
            name="uq_course_enrollment_evidence",
        ),
        Index("ix_active_course_enrollment", "course_id", "user_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    external_course_id: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditEventRecord(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_tenant_created", "tenant_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(80))
    target_id: Mapped[str | None] = mapped_column(String(240))
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UsageCounterRecord(Base):
    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "user_id", "course_id", "usage_date", name="uq_daily_usage_scope"
        ),
        CheckConstraint(
            "agent_turns >= 0 AND reserved_tokens >= 0 AND images >= 0 AND active_turns >= 0",
            name="ck_usage_nonnegative",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[str] = mapped_column(String(120), nullable=False)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    agent_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    images: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

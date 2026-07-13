from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from lecturepilot.db_models import (
    AuditEventRecord,
    CourseEnrollmentRecord,
    CourseRecord,
    ExternalIdentityRecord,
)
from lecturepilot.university_models import UniversityLoginResult


def locked_external_identity(
    session: Session,
    username: str,
) -> ExternalIdentityRecord | None:
    subject = username.strip().casefold()
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:identity_key))"),
        {"identity_key": f"tuebingen:{subject}"},
    )
    return session.scalar(
        select(ExternalIdentityRecord).where(
            ExternalIdentityRecord.provider == "tuebingen",
            ExternalIdentityRecord.subject == subject,
        )
    )


def deactivate_external_enrollments(
    session: Session,
    user_id: UUID,
    tenant_id: str,
) -> None:
    session.execute(
        update(CourseEnrollmentRecord)
        .where(
            CourseEnrollmentRecord.user_id == user_id,
            CourseEnrollmentRecord.source.in_(("alma", "ilias")),
            CourseEnrollmentRecord.course_id.in_(
                select(CourseRecord.id).where(CourseRecord.tenant_id == tenant_id)
            ),
        )
        .values(status="inactive", synced_at=datetime.now(UTC))
    )


def record_login_audit(
    session: Session,
    user_id: UUID,
    tenant_id: str,
    identity: UniversityLoginResult,
) -> None:
    session.add(
        AuditEventRecord(
            tenant_id=tenant_id,
            actor_user_id=user_id,
            event_type="auth.login",
            target_type="user",
            target_id=str(user_id),
            details={
                "sources": sorted(source.value for source in identity.sources_checked),
                "alma_role": identity.alma_current_role,
                "alma_available_roles": identity.alma_available_roles,
            },
        )
    )

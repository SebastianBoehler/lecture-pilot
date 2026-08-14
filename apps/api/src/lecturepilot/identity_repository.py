from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from lecturepilot.database import Database
from lecturepilot.db_models import (
    CourseEnrollmentRecord,
    CourseRecord,
    ExternalIdentityRecord,
    TenantMembershipRecord,
    UserRecord,
)
from lecturepilot.external_course_sync import sync_external_courses
from lecturepilot.external_course_views import latest_external_courses
from lecturepilot.identity_course_sync import (
    complete_course_sync,
    fail_course_sync,
    record_course_sync_source,
    set_source_statuses,
    source_statuses,
)
from lecturepilot.identity_roles import (
    alma_current_role,
    is_professor_identity,
    university_provider_claims,
)
from lecturepilot.identity_sync import (
    deactivate_external_enrollments,
    record_login_audit,
)
from lecturepilot.models import Course, CourseAccessPolicy, TenantRole
from lecturepilot.university_models import (
    ExternalCourseCandidate,
    ExternalCourseSource,
    UniversityCourseSourceStatuses,
    UniversityCourseSyncStatus,
    UniversityLoginResult,
)


@dataclass(frozen=True)
class AccountView:
    user_id: UUID
    username: str
    display_name: str | None
    email: str | None
    tenant_id: str
    account_type: str
    university_role: str | None
    roles: frozenset[TenantRole]
    courses: tuple[Course, ...]
    university_courses: tuple[ExternalCourseCandidate, ...]
    university_course_sync_status: UniversityCourseSyncStatus
    university_course_source_statuses: UniversityCourseSourceStatuses

    @property
    def course_ids(self) -> frozenset[str]:
        return frozenset(course.id for course in self.courses)


class IdentityRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def record_login(self, identity: UniversityLoginResult, *, tenant_id: str) -> AccountView:
        with self.database.session() as session:
            user, external = _upsert_identity(session, identity)
            membership = _membership(session, user.id, tenant_id)
            sync_external_courses(
                session,
                user_id=user.id,
                tenant_id=tenant_id,
                observations=identity.courses,
                checked_sources={source.value for source in identity.sources_checked},
            )
            external.course_sync_id = None
            external.course_sync_status = "ready"
            set_source_statuses(
                external,
                {
                    source: "ready" if source in identity.sources_checked else "error"
                    for source in ExternalCourseSource
                },
            )
            record_login_audit(session, user.id, tenant_id, identity)
            return _account_view(session, user, external, membership)

    def begin_login(
        self,
        identity: UniversityLoginResult,
        *,
        tenant_id: str,
        sync_id: str,
    ) -> AccountView:
        with self.database.session() as session:
            user, external = _upsert_identity(session, identity)
            membership = _membership(session, user.id, tenant_id)
            external.course_sync_id = sync_id
            external.course_sync_status = "loading"
            set_source_statuses(
                external,
                {source: "loading" for source in ExternalCourseSource},
            )
            # A new session must never retain authority from a previous provider snapshot.
            deactivate_external_enrollments(session, user.id, tenant_id)
            record_login_audit(session, user.id, tenant_id, identity)
            return _account_view(session, user, external, membership)

    def record_course_sync_source(
        self,
        identity: UniversityLoginResult,
        *,
        tenant_id: str,
        sync_id: str,
        source: ExternalCourseSource,
    ) -> bool:
        return record_course_sync_source(
            self.database,
            identity,
            tenant_id=tenant_id,
            sync_id=sync_id,
            source=source,
        )

    def complete_course_sync(
        self,
        identity: UniversityLoginResult,
        *,
        tenant_id: str,
        sync_id: str,
    ) -> bool:
        return complete_course_sync(
            self.database,
            identity,
            tenant_id=tenant_id,
            sync_id=sync_id,
        )

    def fail_course_sync(self, *, username: str, sync_id: str) -> bool:
        return fail_course_sync(self.database, username=username, sync_id=sync_id)

    def account(self, *, user_id: UUID, tenant_id: str) -> AccountView | None:
        with self.database.session() as session:
            user = session.get(UserRecord, user_id)
            if user is None or not user.enabled:
                return None
            external = _preferred_identity(session, user.id)
            membership = session.get(TenantMembershipRecord, (user.id, tenant_id))
            if external is None or membership is None:
                return None
            return _account_view(session, user, external, membership)


def _upsert_identity(
    session: Session, identity: UniversityLoginResult
) -> tuple[UserRecord, ExternalIdentityRecord]:
    subject = identity.username.strip().casefold()
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:identity_key))"),
        {"identity_key": f"tuebingen:{subject}"},
    )
    external = session.scalar(
        select(ExternalIdentityRecord).where(
            ExternalIdentityRecord.provider == "tuebingen",
            ExternalIdentityRecord.subject == subject,
        )
    )
    now = datetime.now(UTC)
    if external is None:
        user = UserRecord(display_name=identity.display_name)
        session.add(user)
        session.flush()
        external = ExternalIdentityRecord(
            user_id=user.id,
            provider="tuebingen",
            subject=subject,
            email=identity.email,
            provider_claims=university_provider_claims(identity),
            last_login_at=now,
        )
        session.add(external)
        session.flush()
        return user, external
    user = session.get(UserRecord, external.user_id)
    if user is None or not user.enabled:
        raise PermissionError("This LecturePilot account is disabled.")
    if identity.display_name is not None:
        user.display_name = identity.display_name
    if identity.email is not None:
        external.email = identity.email
    external.provider_claims = university_provider_claims(identity)
    external.last_login_at = now
    user.updated_at = now
    return user, external


def _membership(session: Session, user_id: UUID, tenant_id: str) -> TenantMembershipRecord:
    membership = session.get(TenantMembershipRecord, (user_id, tenant_id))
    if membership is None:
        membership = TenantMembershipRecord(user_id=user_id, tenant_id=tenant_id)
        session.add(membership)
        session.flush()
    return membership


def _account_view(
    session: Session,
    user: UserRecord,
    external: ExternalIdentityRecord,
    membership: TenantMembershipRecord,
) -> AccountView:
    professor_account = is_professor_identity(external.provider, external.provider_claims)
    roles: set[TenantRole] = set()
    if professor_account:
        roles.add(TenantRole.PROFESSOR)
    else:
        roles.add(TenantRole.STUDENT)
    if membership.platform_admin:
        roles.add(TenantRole.TENANT_ADMIN)
    access_conditions = (
        [CourseRecord.owner_user_id == user.id]
        if professor_account
        else [
            CourseEnrollmentRecord.id.is_not(None),
            CourseRecord.access_policy.in_(
                [
                    CourseAccessPolicy.PUBLIC.value,
                    CourseAccessPolicy.PLATFORM_AUTHENTICATED.value,
                ]
            ),
        ]
    )
    courses = session.scalars(
        select(CourseRecord)
        .outerjoin(
            CourseEnrollmentRecord,
            (CourseEnrollmentRecord.course_id == CourseRecord.id)
            & (CourseEnrollmentRecord.user_id == user.id)
            & (CourseEnrollmentRecord.status == "active"),
        )
        .where(
            CourseRecord.tenant_id == membership.tenant_id,
            or_(*access_conditions),
        )
        .distinct()
    ).all()
    return AccountView(
        user_id=user.id,
        username=external.subject,
        display_name=user.display_name,
        email=external.email,
        tenant_id=membership.tenant_id,
        account_type="professor" if professor_account else "student",
        university_role=alma_current_role(external.provider_claims),
        roles=frozenset(roles),
        courses=tuple(_course_view(course) for course in courses),
        university_course_sync_status=cast(
            UniversityCourseSyncStatus,
            external.course_sync_status,
        ),
        university_course_source_statuses=source_statuses(external),
        university_courses=latest_external_courses(
            session,
            user_id=user.id,
            login_at=external.last_login_at,
        ),
    )


def _preferred_identity(session: Session, user_id: UUID) -> ExternalIdentityRecord | None:
    identities = session.scalars(
        select(ExternalIdentityRecord)
        .where(ExternalIdentityRecord.user_id == user_id)
        .order_by(ExternalIdentityRecord.created_at)
    ).all()
    return identities[0] if identities else None


def _course_view(course: CourseRecord) -> Course:
    return Course(
        id=str(course.id),
        title=course.title,
        professor="Professor",
        term=course.term,
        access_policy=course.access_policy,
    )

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from lecturepilot.database import Database
from lecturepilot.db_models import (
    AuditEventRecord,
    CourseEnrollmentRecord,
    CourseRecord,
    ExternalIdentityRecord,
    ProfessorRequestRecord,
    TenantMembershipRecord,
    UserRecord,
)
from lecturepilot.external_course_sync import sync_external_courses
from lecturepilot.external_course_views import latest_external_courses
from lecturepilot.identity_roles import (
    ALMA_AVAILABLE_ROLES_CLAIM,
    ALMA_CURRENT_ROLE_CLAIM,
    alma_current_role,
    identity_account_type,
)
from lecturepilot.models import Course, CourseAccessPolicy, TenantRole
from lecturepilot.university_models import ExternalCourseCandidate, UniversityLoginResult


@dataclass(frozen=True)
class AccountView:
    user_id: UUID
    username: str
    email: str | None
    tenant_id: str
    account_type: str
    university_role: str | None
    roles: frozenset[TenantRole]
    professor_status: str
    courses: tuple[Course, ...]
    university_courses: tuple[ExternalCourseCandidate, ...]

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
            if _is_professor_account(external) and membership.professor_status == "not_requested":
                _create_professor_request(session, user.id, tenant_id, membership)
            sync_external_courses(
                session,
                user_id=user.id,
                tenant_id=tenant_id,
                observations=identity.courses,
                checked_sources={source.value for source in identity.sources_checked},
            )
            session.add(
                AuditEventRecord(
                    tenant_id=tenant_id,
                    actor_user_id=user.id,
                    event_type="auth.login",
                    target_type="user",
                    target_id=str(user.id),
                    details={
                        "sources": sorted(source.value for source in identity.sources_checked),
                        "alma_role": identity.alma_current_role,
                        "alma_available_roles": identity.alma_available_roles,
                    },
                )
            )
            return _account_view(session, user, external, membership)

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
        user = UserRecord()
        session.add(user)
        session.flush()
        external = ExternalIdentityRecord(
            user_id=user.id,
            provider="tuebingen",
            subject=subject,
            email=identity.email,
            provider_claims=_provider_claims(identity),
            last_login_at=now,
        )
        session.add(external)
        session.flush()
        return user, external
    user = session.get(UserRecord, external.user_id)
    if user is None or not user.enabled:
        raise PermissionError("This LecturePilot account is disabled.")
    external.email = identity.email
    external.provider_claims = _provider_claims(identity)
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
    professor_account = _is_professor_account(external)
    roles: set[TenantRole] = set()
    if not professor_account:
        roles.add(TenantRole.STUDENT)
    if professor_account and membership.professor_status == "approved":
        roles.add(TenantRole.PROFESSOR)
    if membership.platform_admin:
        roles.add(TenantRole.TENANT_ADMIN)
    access_conditions = [CourseRecord.owner_user_id == user.id]
    if not professor_account:
        access_conditions.extend(
            [
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
            CourseRecord.archived_at.is_(None),
            CourseRecord.tenant_id == membership.tenant_id,
            or_(*access_conditions),
        )
        .distinct()
    ).all()
    return AccountView(
        user_id=user.id,
        username=user.display_name or external.subject,
        email=external.email,
        tenant_id=membership.tenant_id,
        account_type="professor" if professor_account else "student",
        university_role=alma_current_role(external.provider_claims),
        roles=frozenset(roles),
        professor_status=membership.professor_status,
        courses=tuple(_course_view(course) for course in courses),
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


def _provider_claims(identity: UniversityLoginResult) -> dict[str, object]:
    if identity.alma_current_role is None:
        return {}
    return {
        ALMA_CURRENT_ROLE_CLAIM: identity.alma_current_role,
        ALMA_AVAILABLE_ROLES_CLAIM: identity.alma_available_roles,
    }


def _is_professor_account(identity: ExternalIdentityRecord) -> bool:
    return (
        identity_account_type(
            provider=identity.provider,
            provider_claims=identity.provider_claims,
        )
        == "professor"
    )


def _create_professor_request(
    session: Session,
    user_id: UUID,
    tenant_id: str,
    membership: TenantMembershipRecord,
) -> None:
    now = datetime.now(UTC)
    request = ProfessorRequestRecord(
        user_id=user_id,
        tenant_id=tenant_id,
        status="pending",
        requested_at=now,
    )
    session.add(request)
    membership.professor_status = "pending"
    membership.updated_at = now


def _course_view(course: CourseRecord) -> Course:
    return Course(
        id=str(course.id),
        title=course.title,
        professor="Professor",
        term=course.term,
        access_policy=course.access_policy,
    )

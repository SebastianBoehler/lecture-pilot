from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from lecturepilot.database import Database
from lecturepilot.core.db_models import (
    CourseEnrollmentRecord,
    CourseRecord,
    ExternalIdentityRecord,
    TenantMembershipRecord,
    UserRecord,
)
from lecturepilot.courses.external_course_views import latest_external_courses
from lecturepilot.identity.identity_roles import alma_current_role, is_professor_identity
from lecturepilot.core.models import Course, CourseAccessPolicy, TenantRole
from lecturepilot.courses.university_models import ExternalCourseCandidate


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

    @property
    def course_ids(self) -> frozenset[str]:
        return frozenset(course.id for course in self.courses)


class IdentityRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

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

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select

from lecturepilot.database import Database
from lecturepilot.db_models import (
    AuditEventRecord,
    CourseEnrollmentRecord,
    CourseRecord,
    TenantMembershipRecord,
)
from lecturepilot.models import (
    Course,
    CourseAccessPolicy,
    CourseWorkspaceSetupInput,
)


class CourseRepositoryError(ValueError):
    pass


class CourseRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(
        self,
        *,
        user_id: UUID,
        tenant_id: str,
        setup: CourseWorkspaceSetupInput,
        default_term: str,
    ) -> Course:
        with self.database.session() as session:
            return self._create_in_session(
                session,
                user_id=user_id,
                tenant_id=tenant_id,
                setup=setup,
                default_term=default_term,
            )

    def _create_in_session(
        self,
        session,
        *,
        user_id: UUID,
        tenant_id: str,
        setup: CourseWorkspaceSetupInput,
        default_term: str,
    ) -> Course:
        membership = session.get(TenantMembershipRecord, (user_id, tenant_id))
        if membership is None or membership.professor_status != "approved":
            raise CourseRepositoryError("Approved professor access is required.")
        term = setup.term or default_term
        course = CourseRecord(
            tenant_id=tenant_id,
            owner_user_id=user_id,
            title=setup.course_title.strip(),
            term=term,
            access_policy=setup.access_policy.value,
        )
        session.add(course)
        session.flush()
        session.add(
            AuditEventRecord(
                tenant_id=tenant_id,
                actor_user_id=user_id,
                event_type="course.created",
                target_type="course",
                target_id=str(course.id),
                details={"enrollment_matching": "normalized_title_and_term"},
            )
        )
        return _course(course)

    def get(self, *, course_id: str, tenant_id: str) -> Course | None:
        identifier = _uuid(course_id)
        if identifier is None:
            return None
        with self.database.session() as session:
            record = session.scalar(
                select(CourseRecord).where(
                    CourseRecord.id == identifier,
                    CourseRecord.tenant_id == tenant_id,
                    CourseRecord.archived_at.is_(None),
                )
            )
            return _course(record) if record else None

    def owned_course(self, *, user_id: UUID, tenant_id: str, course_id: str) -> Course:
        identifier = _uuid(course_id)
        if identifier is None:
            raise CourseRepositoryError("Course id is invalid.")
        with self.database.session() as session:
            record = session.scalar(
                select(CourseRecord).where(
                    CourseRecord.id == identifier,
                    CourseRecord.tenant_id == tenant_id,
                    CourseRecord.owner_user_id == user_id,
                    CourseRecord.archived_at.is_(None),
                )
            )
            if record is None:
                raise CourseRepositoryError("Course ownership is required.")
            return _course(record)

    def list_accessible(self, *, user_id: UUID, tenant_id: str) -> list[Course]:
        with self.database.session() as session:
            records = session.scalars(
                select(CourseRecord)
                .outerjoin(
                    CourseEnrollmentRecord,
                    (CourseEnrollmentRecord.course_id == CourseRecord.id)
                    & (CourseEnrollmentRecord.user_id == user_id)
                    & (CourseEnrollmentRecord.status == "active"),
                )
                .where(
                    CourseRecord.tenant_id == tenant_id,
                    CourseRecord.archived_at.is_(None),
                    or_(
                        CourseRecord.owner_user_id == user_id,
                        CourseEnrollmentRecord.id.is_not(None),
                        CourseRecord.access_policy.in_(
                            [
                                CourseAccessPolicy.PUBLIC.value,
                                CourseAccessPolicy.PLATFORM_AUTHENTICATED.value,
                            ]
                        ),
                    ),
                )
                .distinct()
                .order_by(CourseRecord.created_at)
            ).all()
            return [_course(record) for record in records]

    def list_owned(self, *, user_id: UUID, tenant_id: str) -> list[Course]:
        with self.database.session() as session:
            records = session.scalars(
                select(CourseRecord)
                .where(
                    CourseRecord.tenant_id == tenant_id,
                    CourseRecord.owner_user_id == user_id,
                    CourseRecord.archived_at.is_(None),
                )
                .order_by(CourseRecord.created_at)
            ).all()
            return [_course(record) for record in records]

    def is_owner(self, *, user_id: UUID, tenant_id: str, course_id: str) -> bool:
        identifier = _uuid(course_id)
        if identifier is None:
            return False
        with self.database.session() as session:
            return (
                session.scalar(
                    select(CourseRecord.id).where(
                        CourseRecord.id == identifier,
                        CourseRecord.tenant_id == tenant_id,
                        CourseRecord.owner_user_id == user_id,
                        CourseRecord.archived_at.is_(None),
                    )
                )
                is not None
            )

    def can_learn(self, *, user_id: UUID, tenant_id: str, course_id: str) -> bool:
        identifier = _uuid(course_id)
        if identifier is None:
            return False
        with self.database.session() as session:
            course = session.scalar(
                select(CourseRecord).where(
                    CourseRecord.id == identifier,
                    CourseRecord.tenant_id == tenant_id,
                    CourseRecord.archived_at.is_(None),
                )
            )
            if course is None:
                return False
            if course.owner_user_id == user_id:
                return True
            if course.access_policy in {
                CourseAccessPolicy.PUBLIC.value,
                CourseAccessPolicy.PLATFORM_AUTHENTICATED.value,
            }:
                return True
            return (
                session.scalar(
                    select(CourseEnrollmentRecord.id).where(
                        CourseEnrollmentRecord.course_id == identifier,
                        CourseEnrollmentRecord.user_id == user_id,
                        CourseEnrollmentRecord.status == "active",
                    )
                )
                is not None
            )

    def archive(self, *, user_id: UUID, tenant_id: str, course_id: str) -> bool:
        identifier = _uuid(course_id)
        if identifier is None:
            return False
        with self.database.session() as session:
            course = session.scalar(
                select(CourseRecord).where(
                    CourseRecord.id == identifier,
                    CourseRecord.tenant_id == tenant_id,
                    CourseRecord.owner_user_id == user_id,
                    CourseRecord.archived_at.is_(None),
                )
            )
            if course is None:
                return False
            course.archived_at = datetime.now(UTC)
            session.add(
                AuditEventRecord(
                    tenant_id=tenant_id,
                    actor_user_id=user_id,
                    event_type="course.archived",
                    target_type="course",
                    target_id=course_id,
                )
            )
            return True


def _course(record: CourseRecord) -> Course:
    return Course(
        id=str(record.id),
        title=record.title,
        professor="Professor",
        term=record.term,
        access_policy=record.access_policy,
    )


def _uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None

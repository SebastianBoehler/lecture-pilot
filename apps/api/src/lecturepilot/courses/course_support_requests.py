from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, and_, delete, distinct, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from lecturepilot.core.db_models import (
    AuditEventRecord,
    CourseSupportRequestRecord,
    ExternalCourseObservationRecord,
    TenantMembershipRecord,
)
from lecturepilot.courses.course_support_models import CourseSupportKey, CourseSupportStatus
from lecturepilot.database import Database

Request = CourseSupportRequestRecord
Observation = ExternalCourseObservationRecord


class CourseNotObservedError(LookupError):
    """The session user has no stored university observation for the requested course."""


def tenant_member_ids(tenant_id: str) -> Select:
    return select(TenantMembershipRecord.user_id).where(
        TenantMembershipRecord.tenant_id == tenant_id
    )


class CourseSupportRequests:
    """Per-learner course support requests; counts are aggregated across tenant members."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def list(self, *, user_id: UUID, tenant_id: str) -> list[CourseSupportStatus]:
        with self.database.session() as session:
            observed = session.execute(
                select(Observation.source, Observation.external_course_id, Observation.term)
                .where(Observation.user_id == user_id)
                .order_by(Observation.term, Observation.source, Observation.external_course_id)
            ).all()
            own = {
                tuple(row)
                for row in session.execute(
                    select(Request.source, Request.external_course_id, Request.term).where(
                        Request.user_id == user_id
                    )
                )
            }
            counts = _counts_for_observed_courses(session, user_id=user_id, tenant_id=tenant_id)
        return [
            CourseSupportStatus(
                source=key[0],
                external_course_id=key[1],
                term=key[2],
                requested=tuple(key) in own,
                request_count=counts.get(tuple(key), 0),
            )
            for key in observed
        ]

    def request(
        self, *, user_id: UUID, tenant_id: str, key: CourseSupportKey
    ) -> CourseSupportStatus:
        with self.database.session() as session:
            _require_observation(session, user_id=user_id, key=key)
            created = session.scalar(
                insert(Request)
                .values(
                    id=uuid4(),
                    user_id=user_id,
                    source=key.source.value,
                    external_course_id=key.external_course_id,
                    term=key.term,
                    created_at=datetime.now(UTC),
                )
                .on_conflict_do_nothing(constraint="uq_user_course_support")
                .returning(Request.id)
            )
            if created is not None:
                _audit(session, tenant_id, user_id, "course_support.requested", created, key)
            return _status(session, user_id=user_id, tenant_id=tenant_id, key=key)

    def withdraw(
        self, *, user_id: UUID, tenant_id: str, key: CourseSupportKey
    ) -> CourseSupportStatus:
        with self.database.session() as session:
            _require_observation(session, user_id=user_id, key=key)
            removed = session.scalar(
                delete(Request)
                .where(Request.user_id == user_id, *_key_filter(Request, key))
                .returning(Request.id)
            )
            if removed is not None:
                _audit(session, tenant_id, user_id, "course_support.withdrawn", removed, key)
            return _status(session, user_id=user_id, tenant_id=tenant_id, key=key)


def _require_observation(session: Session, *, user_id: UUID, key: CourseSupportKey) -> None:
    observed = session.scalar(
        select(Observation.id).where(Observation.user_id == user_id, *_key_filter(Observation, key))
    )
    if observed is None:
        raise CourseNotObservedError("This course is not among your university courses.")


def _status(
    session: Session, *, user_id: UUID, tenant_id: str, key: CourseSupportKey
) -> CourseSupportStatus:
    requested = session.scalar(
        select(Request.id).where(Request.user_id == user_id, *_key_filter(Request, key))
    )
    count = session.scalar(
        select(func.count(distinct(Request.user_id))).where(
            Request.user_id.in_(tenant_member_ids(tenant_id)), *_key_filter(Request, key)
        )
    )
    return CourseSupportStatus(
        **key.model_dump(), requested=requested is not None, request_count=count or 0
    )


def _counts_for_observed_courses(
    session: Session, *, user_id: UUID, tenant_id: str
) -> dict[tuple[str, str, str], int]:
    rows = session.execute(
        select(
            Request.source,
            Request.external_course_id,
            Request.term,
            func.count(distinct(Request.user_id)),
        )
        .join(
            Observation,
            and_(
                Observation.user_id == user_id,
                Observation.source == Request.source,
                Observation.external_course_id == Request.external_course_id,
                Observation.term == Request.term,
            ),
        )
        .where(Request.user_id.in_(tenant_member_ids(tenant_id)))
        .group_by(Request.source, Request.external_course_id, Request.term)
    ).all()
    return {(source, course_id, term): count for source, course_id, term, count in rows}


def _key_filter(record: type[Request] | type[Observation], key: CourseSupportKey) -> tuple:
    return (
        record.source == key.source.value,
        record.external_course_id == key.external_course_id,
        record.term == key.term,
    )


def _audit(
    session: Session,
    tenant_id: str,
    user_id: UUID,
    event_type: str,
    request_id: UUID,
    key: CourseSupportKey,
) -> None:
    # Categorical only: the course title or other learner-linked text never enters audit rows.
    session.add(
        AuditEventRecord(
            tenant_id=tenant_id,
            actor_user_id=user_id,
            event_type=event_type,
            target_type="course_support_request",
            target_id=str(request_id),
            details={"source": key.source.value},
        )
    )

from __future__ import annotations

from datetime import UTC, datetime
import unicodedata
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from lecturepilot.db_models import (
    AuditEventRecord,
    CourseEnrollmentRecord,
    CourseExternalRefRecord,
    CourseRecord,
    ExternalCourseObservationRecord,
)
from lecturepilot.models import CourseAccessPolicy
from lecturepilot.metadata_events import emit_metadata_event
from lecturepilot.university_models import ExternalCourseCandidate


def sync_external_courses(
    session: Session,
    *,
    user_id: UUID,
    tenant_id: str,
    observations: list[ExternalCourseCandidate],
    checked_sources: set[str],
) -> None:
    _store_observations(session, user_id, observations)
    _sync_enrollments(
        session,
        user_id,
        tenant_id,
        observations,
        checked_sources,
    )


def _store_observations(
    session: Session, user_id: UUID, courses: list[ExternalCourseCandidate]
) -> None:
    now = datetime.now(UTC)
    for course in courses:
        observation = session.scalar(
            select(ExternalCourseObservationRecord).where(
                ExternalCourseObservationRecord.user_id == user_id,
                ExternalCourseObservationRecord.source == course.source.value,
                ExternalCourseObservationRecord.external_course_id == course.external_course_id,
                ExternalCourseObservationRecord.term == course.term,
            )
        )
        values = course.model_dump(mode="json")
        values.pop("source", None)
        if observation is None:
            session.add(
                ExternalCourseObservationRecord(
                    user_id=user_id,
                    source=course.source.value,
                    observed_at=now,
                    **values,
                )
            )
            continue
        for key, value in values.items():
            setattr(observation, key, value)
        observation.observed_at = now


def _sync_enrollments(
    session: Session,
    user_id: UUID,
    tenant_id: str,
    observations: list[ExternalCourseCandidate],
    checked_sources: set[str],
) -> None:
    now = datetime.now(UTC)
    if checked_sources:
        session.execute(
            update(CourseEnrollmentRecord)
            .where(
                CourseEnrollmentRecord.user_id == user_id,
                CourseEnrollmentRecord.source.in_(checked_sources),
                CourseEnrollmentRecord.course_id.in_(
                    select(CourseRecord.id).where(CourseRecord.tenant_id == tenant_id)
                ),
            )
            .values(status="inactive", synced_at=now)
        )
    for observation in observations:
        try:
            with session.begin_nested():
                _sync_observation(session, user_id, tenant_id, observation, now)
        except IntegrityError as exc:
            emit_metadata_event(
                "university_course_sync.observation_skipped",
                error=True,
                exception_type=type(exc).__name__,
                root_cause_type=type(exc.orig).__name__,
                outcome="skipped_course",
            )


def _sync_observation(
    session: Session,
    user_id: UUID,
    tenant_id: str,
    observation: ExternalCourseCandidate,
    now: datetime,
) -> None:
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:course_key))"),
        {
            "course_key": (
                f"course-ref:{tenant_id}:{observation.source.value}:"
                f"{observation.external_course_id}:{observation.term}"
            )
        },
    )
    external_ref = _external_course_ref(session, tenant_id, observation)
    if external_ref is None:
        external_ref = _match_and_link_course(session, user_id, tenant_id, observation)
        if external_ref is None:
            return
    enrollment = session.scalar(
        select(CourseEnrollmentRecord).where(
            CourseEnrollmentRecord.course_id == external_ref.course_id,
            CourseEnrollmentRecord.user_id == user_id,
            CourseEnrollmentRecord.source == observation.source.value,
            CourseEnrollmentRecord.external_course_id == observation.external_course_id,
        )
    )
    if enrollment is None:
        session.add(
            CourseEnrollmentRecord(
                course_id=external_ref.course_id,
                user_id=user_id,
                source=observation.source.value,
                external_course_id=observation.external_course_id,
                status="active",
                synced_at=now,
            )
        )
    else:
        enrollment.status = "active"
        enrollment.synced_at = now


def _external_course_ref(
    session: Session,
    tenant_id: str,
    observation: ExternalCourseCandidate,
) -> CourseExternalRefRecord | None:
    return session.scalar(
        select(CourseExternalRefRecord).where(
            CourseExternalRefRecord.tenant_id == tenant_id,
            CourseExternalRefRecord.source == observation.source.value,
            CourseExternalRefRecord.external_course_id == observation.external_course_id,
            CourseExternalRefRecord.term == observation.term,
        )
    )


def _match_and_link_course(
    session: Session,
    user_id: UUID,
    tenant_id: str,
    observation: ExternalCourseCandidate,
) -> CourseExternalRefRecord | None:
    candidates = session.scalars(
        select(CourseRecord).where(
            CourseRecord.tenant_id == tenant_id,
            CourseRecord.term == observation.term,
            CourseRecord.access_policy == CourseAccessPolicy.TUEBINGEN_ENROLLED.value,
        )
    ).all()
    title_key = _course_title_key(observation.title)
    matches = [course for course in candidates if _course_title_key(course.title) == title_key]
    if len(matches) != 1:
        return None
    external_ref = CourseExternalRefRecord(
        course_id=matches[0].id,
        tenant_id=tenant_id,
        source=observation.source.value,
        external_course_id=observation.external_course_id,
        term=observation.term,
        number=observation.number,
        title=observation.title,
        organization=observation.organization,
        instructor=observation.instructor,
        display_url=observation.display_url,
    )
    session.add(external_ref)
    session.flush()
    session.add(
        AuditEventRecord(
            tenant_id=tenant_id,
            actor_user_id=user_id,
            event_type="course.external_ref_discovered",
            target_type="course",
            target_id=str(matches[0].id),
            details={"source": observation.source.value},
        )
    )
    return external_ref


def _course_title_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())

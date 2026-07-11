from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from lecturepilot.db_models import ExternalCourseObservationRecord
from lecturepilot.university_models import ExternalCourseCandidate, ExternalCourseSource


def latest_external_courses(
    session: Session,
    *,
    user_id: UUID,
    login_at: datetime,
) -> tuple[ExternalCourseCandidate, ...]:
    observations = session.scalars(
        select(ExternalCourseObservationRecord)
        .where(
            ExternalCourseObservationRecord.user_id == user_id,
            ExternalCourseObservationRecord.observed_at >= login_at,
        )
        .order_by(
            ExternalCourseObservationRecord.title,
            ExternalCourseObservationRecord.source,
        )
    ).all()
    return tuple(_candidate(observation) for observation in observations)


def _candidate(observation: ExternalCourseObservationRecord) -> ExternalCourseCandidate:
    return ExternalCourseCandidate(
        source=ExternalCourseSource(observation.source),
        external_course_id=observation.external_course_id,
        term=observation.term,
        number=observation.number,
        title=observation.title,
        organization=observation.organization,
        instructor=observation.instructor,
        display_url=observation.display_url,
    )

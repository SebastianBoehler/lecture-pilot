from __future__ import annotations

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from lecturepilot.lecture_access_models import (
    CourseAccessPolicy,
    LectureAccessRule,
    LectureReleaseStatus,
    PublicationMode,
)
from lecturepilot.models import Course, Lecture


TENANT_TIMEZONE = ZoneInfo("Europe/Berlin")
UNIVERSITY_AUDIENCES = frozenset(
    {
        CourseAccessPolicy.PUBLIC,
        CourseAccessPolicy.PLATFORM_AUTHENTICATED,
    }
)


def course_default_rule(course: Course) -> LectureAccessRule:
    if course.default_publication_mode not in {
        PublicationMode.HIDDEN,
        PublicationMode.ON_LECTURE_DATE,
    }:
        raise ValueError("Course defaults support hidden or lecture-date publication only.")
    return LectureAccessRule(
        audience=course.access_policy,
        publication_mode=course.default_publication_mode,
    )


def effective_rule(course: Course, lecture: Lecture) -> LectureAccessRule:
    return lecture.access_override or course_default_rule(course)


def effective_publication_at(
    lecture: Lecture,
    rule: LectureAccessRule,
) -> datetime | None:
    if rule.publication_mode is PublicationMode.HIDDEN:
        return None
    lecture_floor = datetime.combine(lecture.date, time.min, tzinfo=TENANT_TIMEZONE)
    requested = rule.publication_at or lecture_floor
    return max(lecture_floor, requested).astimezone(UTC)


def release_status(
    lecture: Lecture,
    rule: LectureAccessRule,
    *,
    now: datetime | None = None,
) -> LectureReleaseStatus:
    available_at = effective_publication_at(lecture, rule)
    if available_at is None:
        return LectureReleaseStatus.HIDDEN
    current = _aware_now(now)
    if current < available_at:
        return LectureReleaseStatus.SCHEDULED
    return LectureReleaseStatus.RELEASED


def audience_allows(
    rule: LectureAccessRule,
    *,
    is_owner: bool,
    is_enrolled: bool,
    same_tenant: bool,
) -> bool:
    if is_owner:
        return True
    if not same_tenant or rule.audience is CourseAccessPolicy.INSTRUCTORS_ONLY:
        return False
    if rule.audience is CourseAccessPolicy.TUEBINGEN_ENROLLED:
        return is_enrolled
    return rule.audience in UNIVERSITY_AUDIENCES


def can_consume_lecture(
    course: Course,
    lecture: Lecture,
    *,
    is_owner: bool,
    is_enrolled: bool,
    same_tenant: bool,
    now: datetime | None = None,
) -> bool:
    if is_owner:
        return True
    rule = effective_rule(course, lecture)
    return (
        audience_allows(
            rule,
            is_owner=False,
            is_enrolled=is_enrolled,
            same_tenant=same_tenant,
        )
        and release_status(lecture, rule, now=now) is LectureReleaseStatus.RELEASED
    )


def can_list_lecture(
    course: Course,
    lecture: Lecture,
    *,
    content_ready: bool,
    is_owner: bool,
    is_enrolled: bool,
    same_tenant: bool,
    now: datetime | None = None,
) -> bool:
    if is_owner:
        return True
    if not content_ready:
        return False
    rule = effective_rule(course, lecture)
    if not audience_allows(
        rule,
        is_owner=False,
        is_enrolled=is_enrolled,
        same_tenant=same_tenant,
    ):
        return False
    status = release_status(lecture, rule, now=now)
    return status is LectureReleaseStatus.RELEASED or (
        status is LectureReleaseStatus.SCHEDULED and is_enrolled
    )


def is_university_audience(audience: CourseAccessPolicy) -> bool:
    return audience in UNIVERSITY_AUDIENCES


def _aware_now(value: datetime | None) -> datetime:
    current = value or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("Current time must be timezone-aware.")
    return current.astimezone(UTC)

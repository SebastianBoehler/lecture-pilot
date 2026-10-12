from datetime import date, datetime, timedelta

from lecturepilot.courses.lecture_access_models import LectureAccessRule, LectureReleaseStatus
from lecturepilot.courses.lecture_access_policy import TENANT_TIMEZONE, release_status
from lecturepilot.core.models import Lecture


def _lecture(day: date) -> Lecture:
    return Lecture(id=f"l-{day.isoformat()}", course_id="c1", title="Lecture", date=day)


def test_lecture_date_rule_unlocks_only_lectures_on_or_before_today() -> None:
    rule = LectureAccessRule()
    now = datetime(2026, 6, 5, 9, 0, tzinfo=TENANT_TIMEZONE)

    assert release_status(_lecture(date(2026, 6, 4)), rule, now=now) is (
        LectureReleaseStatus.RELEASED
    )
    assert release_status(_lecture(date(2026, 6, 5)), rule, now=now) is (
        LectureReleaseStatus.RELEASED
    )
    assert release_status(_lecture(date(2026, 6, 6)), rule, now=now) is (
        LectureReleaseStatus.SCHEDULED
    )


def test_lecture_date_rule_unlocks_at_tenant_midnight() -> None:
    rule = LectureAccessRule()
    lecture = _lecture(date(2026, 6, 5))
    midnight = datetime(2026, 6, 5, 0, 0, tzinfo=TENANT_TIMEZONE)

    assert release_status(lecture, rule, now=midnight - timedelta(seconds=1)) is (
        LectureReleaseStatus.SCHEDULED
    )
    assert release_status(lecture, rule, now=midnight) is LectureReleaseStatus.RELEASED

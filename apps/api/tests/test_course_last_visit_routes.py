import json
from datetime import UTC, datetime, timedelta

from auth_helpers import professor_headers, student_headers
from learner_study_test_helpers import COURSE_ID, learner, study_client
from lecturepilot.course_last_visit import (
    CourseVisitStore,
    ReleasedLecture,
    new_lecture_ids,
)

VISITS = f"/courses/{COURSE_ID}/visits"


def _lecture_visit(lecture_id: str) -> str:
    return f"/courses/{COURSE_ID}/lectures/{lecture_id}/visits"


def test_first_visit_has_no_badges_and_later_visit_flags_newly_published(tmp_path) -> None:
    client = study_client(tmp_path)
    layout = client.app.state.canvas_workspace.layout

    first = client.post(VISITS, headers=learner())
    assert first.status_code == 200, first.text
    assert first.json()["new_lecture_ids"] == []
    assert first.json()["previous_visit_at"] is None

    CourseVisitStore(layout).record_course_visit(
        user_id="student-b",
        course_id=COURSE_ID,
        now=datetime.now(UTC) - timedelta(hours=2),
    )
    later = client.post(VISITS, headers=learner("student-b"))
    assert later.status_code == 200
    assert sorted(later.json()["new_lecture_ids"]) == ["lecture-open", "lecture-two"]

    opened = client.post(_lecture_visit("lecture-open"), headers=learner("student-b"))
    assert opened.status_code == 204
    reload = client.post(VISITS, headers=learner("student-b"))
    assert reload.json()["new_lecture_ids"] == ["lecture-two"]

    path = layout.user_course_root("student-b", COURSE_ID) / "last-visit.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert "student-b" not in str(path)
    assert set(stored["opened_lectures"]) == {"lecture-open"}


def test_visits_are_learner_only_and_access_checked(tmp_path) -> None:
    client = study_client(tmp_path)
    outsider = student_headers("outsider", course_ids=[])
    preview = {**professor_headers(), "X-LecturePilot-Learner-Preview": "professor"}

    assert client.post(VISITS).status_code == 401
    assert client.post(VISITS, headers=outsider).status_code == 404
    assert client.post(VISITS, headers=professor_headers()).status_code == 403
    assert client.post(VISITS, headers=preview).status_code == 403
    assert client.post(_lecture_visit("lecture-locked"), headers=learner()).status_code == 403
    assert client.post(_lecture_visit("lecture-hidden"), headers=learner()).status_code == 404
    assert client.post(_lecture_visit("../escape"), headers=learner()).status_code == 404
    layout = client.app.state.canvas_workspace.layout
    assert not (layout.user_course_root("outsider", COURSE_ID) / "last-visit.json").exists()


def test_visit_session_gap_and_reopened_lecture_rules(tmp_path) -> None:
    client = study_client(tmp_path)
    store = CourseVisitStore(client.app.state.canvas_workspace.layout)
    start = datetime(2026, 1, 1, 9, tzinfo=UTC)

    store.record_course_visit(user_id="u", course_id=COURSE_ID, now=start)
    same = store.record_course_visit(
        user_id="u", course_id=COURSE_ID, now=start + timedelta(minutes=10)
    )
    assert same.previous_visit_at is None
    next_day = store.record_course_visit(
        user_id="u", course_id=COURSE_ID, now=start + timedelta(days=1)
    )
    assert next_day.previous_visit_at == start + timedelta(minutes=10)

    released = start + timedelta(hours=5)
    store.record_lecture_opened(user_id="u", course_id=COURSE_ID, lecture_id="old-open", now=start)
    state = store.record_course_visit(
        user_id="u", course_id=COURSE_ID, now=start + timedelta(days=1, minutes=5)
    )
    lectures = [
        ReleasedLecture(id="before", released_at=start),
        ReleasedLecture(id="old-open", released_at=released),
        ReleasedLecture(id="fresh", released_at=released),
    ]
    assert new_lecture_ids(state, lectures) == ["old-open", "fresh"]

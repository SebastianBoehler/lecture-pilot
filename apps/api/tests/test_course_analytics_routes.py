from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers
from lecturepilot.analytics import AnalyticsStore
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.models import AttendanceStatus, Course, CourseWorkspaceResult, Lecture
from test_analytics_routes import _canvas_document, _client


def test_course_analytics_roll_up_published_lectures_without_double_counting_learners(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path)
    _publish_second_lecture(client, tmp_path)
    block = _canvas_document(tmp_path).sections[0].blocks[0]
    client.app.state.analytics_store = AnalyticsStore(client.app.state.canvas_workspace.layout)
    store = client.app.state.analytics_store
    for lecture_id, user_id, option_index, attendance in [
        ("lecture-01", "student-a", 1, AttendanceStatus.PRESENT),
        ("lecture-02", "student-a", 0, AttendanceStatus.PRESENT),
        ("lecture-02", "student-b", 1, AttendanceStatus.ABSENT),
    ]:
        store.record_quiz_answer(
            course_id="demo-course",
            lecture_id=lecture_id,
            user_id=user_id,
            attendance=attendance,
            block=block,
            option_index=option_index,
        )
    original_read_text = Path.read_text

    def reject_whole_event_log_read(path: Path, *args, **kwargs) -> str:
        if path.name == "events.jsonl":
            raise AssertionError("course analytics must stream event logs")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", reject_whole_event_log_read)

    response = client.get(
        "/admin/courses/demo-course/analytics",
        headers=professor_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_events"] == 3
    assert payload["unique_learners"] == 2
    assert payload["quiz_attempts"] == 3
    assert payload["quiz_correct_attempts"] == 2
    assert payload["quiz_rate"] == 0.6667
    assert payload["gate_rate"] is None
    assert [item["lecture_id"] for item in payload["lectures"]] == [
        "lecture-01",
        "lecture-02",
    ]
    assert payload["lectures"][0]["quiz_rate"] == 1.0
    assert payload["lectures"][1]["quiz_rate"] == 0.5


def _publish_second_lecture(client: TestClient, tmp_path: Path) -> None:
    write_course_workspace(
        client.app.state.canvas_workspace.course_media_root("demo-course"),
        CourseWorkspaceResult(
            course=Course(
                id="demo-course",
                title="Demo Course",
                professor="Prof. Demo",
                term="Sommer 2026",
            ),
            lectures=[
                Lecture(
                    id="lecture-02",
                    course_id="demo-course",
                    title="Second lecture",
                    date=date(2026, 6, 8),
                )
            ],
            active_lecture_id="lecture-02",
        ),
    )
    client.app.state.canvas_workspace.write_course_canvas(
        _canvas_document(tmp_path).model_copy(
            update={
                "id": "demo-course-lecture-02",
                "lecture_id": "lecture-02",
                "title": "Second lecture",
            }
        )
    )

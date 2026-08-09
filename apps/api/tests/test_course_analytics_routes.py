from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture
from canvas_workspace_fixtures import publish_course_canvas
from test_analytics_routes import _canvas_document, _client


def test_course_analytics_roll_up_published_lectures_without_double_counting_learners(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    _publish_second_lecture(client, tmp_path)
    for lecture_id, user_id, option_index, attendance in [
        ("lecture-01", "student-a", 1, "present"),
        ("lecture-02", "student-a", 0, "present"),
        ("lecture-02", "student-b", 1, "absent"),
    ]:
        response = client.post(
            f"/courses/demo-course/lectures/{lecture_id}/analytics/quiz-answer",
            headers=student_headers(user_id),
            json={
                "attendance": attendance,
                "attempt_id": f"{user_id}-{lecture_id}-1",
                "block_id": "risk-check",
                "option_index": option_index,
            },
        )
        assert response.status_code == 200
    response = client.get(
        "/admin/courses/demo-course/analytics",
        headers=professor_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["activity_events"] == 3
    assert payload["unique_learners"] == 2
    assert payload["quiz_first_attempt"]["sample_size"] == 2
    assert payload["quiz_first_attempt"]["rate"] is None
    assert payload["quiz_first_attempt"]["data_status"] == "insufficient_data"
    assert payload["independent_first_pass"]["sample_size"] == 0
    assert [item["lecture_id"] for item in payload["lectures"]] == [
        "lecture-01",
        "lecture-02",
    ]
    assert payload["lectures"][0]["quiz_first_attempt"]["sample_size"] == 1
    assert payload["lectures"][1]["quiz_first_attempt"]["sample_size"] == 2


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
    publish_course_canvas(
        client.app.state.canvas_workspace,
        _canvas_document(tmp_path).model_copy(
            update={
                "id": "demo-course-lecture-02",
                "lecture_id": "lecture-02",
                "title": "Second lecture",
            }
        ),
    )

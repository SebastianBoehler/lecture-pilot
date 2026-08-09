from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from canvas_workspace_fixtures import publish_course_canvas
from lecturepilot.canvas_models import CanvasBlock
from test_analytics_routes import _canvas_document, _client


def test_lecture_headlines_reduce_assessments_within_each_learner_first(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    document = _canvas_document(tmp_path)
    section = document.sections[0]
    quizzes = [_quiz(f"quiz-{index}") for index in range(1, 11)]
    publish_course_canvas(
        client.app.state.canvas_workspace,
        document.model_copy(update={"sections": [section.model_copy(update={"blocks": quizzes})]}),
    )

    for learner in ("student-a", "student-b", "student-c", "student-d", "student-e"):
        _answer(client, learner, "quiz-1", 1 if learner == "student-a" else 0)
    for index in range(2, 11):
        _answer(client, "student-a", f"quiz-{index}", 0)

    lecture = client.get(
        "/admin/courses/demo-course/lectures/lecture-01/analytics",
        headers=professor_headers(),
    )
    course = client.get("/admin/courses/demo-course/analytics", headers=professor_headers())

    assert lecture.status_code == 200
    assert course.status_code == 200
    expected = {
        "evidence_type": "quiz_first_attempt",
        "sample_size": 5,
        "data_status": "available",
        "rate": 0.02,
    }
    assert lecture.json()["quiz_first_attempt"] == expected
    assert course.json()["quiz_first_attempt"] == expected


def test_quiz_outcome_retry_repairs_cross_file_partial_write_without_duplicates(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    store = client.app.state.analytics_store
    outcome_path = store._events_path("demo-course", "lecture-01")
    outcome_path.mkdir(parents=True)
    request = {
        "attendance": "present",
        "attempt_id": "student-a-risk-check-retry",
        "block_id": "risk-check",
        "option_index": 1,
        "publication_version": 1,
    }

    failing_client = TestClient(client.app, raise_server_exceptions=False)
    failed = failing_client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=student_headers("student-a"),
        json=request,
    )
    assert failed.status_code == 500
    outcome_path.rmdir()

    repaired = client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=student_headers("student-a"),
        json=request,
    )
    replay = client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=student_headers("student-a"),
        json=request,
    )

    assert repaired.status_code == 200
    assert replay.status_code == 200
    assert repaired.json()["attempt_index"] == 1
    assert replay.json()["attempt_index"] == 1
    assert len(store.events(course_id="demo-course", lecture_id="lecture-01")) == 1


def _quiz(block_id: str) -> CanvasBlock:
    return CanvasBlock(
        id=block_id,
        type="component",
        component_id=block_id,
        component_type="single_choice_quiz",
        caption=f"Retrieval check {block_id}",
        text=f"Which option is correct for {block_id}?",
        items=["Incorrect", "Correct"],
        option_ids=["incorrect", "correct"],
        answer_index=1,
    )


def _answer(client: TestClient, learner: str, block_id: str, option_index: int) -> None:
    state = client.get(
        "/courses/demo-course/lectures/lecture-01/learner-state",
        headers=student_headers(learner),
    )
    assert state.status_code == 200
    response = client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=student_headers(learner),
        json={
            "attendance": "present",
            "attempt_id": f"{learner}-{block_id}-attempt-1",
            "block_id": block_id,
            "option_index": option_index,
            "publication_version": state.json()["publication_version"],
        },
    )
    assert response.status_code == 200

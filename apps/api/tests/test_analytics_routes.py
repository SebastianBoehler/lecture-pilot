from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from canvas_workspace_fixtures import configure_canvas_workspace, publish_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.models import (
    Course,
    CourseWorkspaceResult,
    Lecture,
)


def test_quiz_answers_are_recorded_as_aggregate_lecture_analytics(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=student_headers("student-a"),
        json={
            "attendance": "present",
            "attempt_id": "student-a-risk-check-1",
            "block_id": "risk-check",
            "option_index": 1,
            "publication_version": 1,
        },
    )
    assert response.status_code == 200
    assert response.json()["correct"] is True

    second = client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=student_headers("student-b"),
        json={
            "attendance": "absent",
            "attempt_id": "student-b-risk-check-1",
            "block_id": "risk-check",
            "option_index": 0,
            "publication_version": 1,
        },
    )
    assert second.status_code == 200
    assert second.json()["correct"] is False

    summary = client.get(
        "/admin/courses/demo-course/lectures/lecture-01/analytics",
        headers=professor_headers(),
    )

    assert summary.status_code == 200
    payload = summary.json()
    assert payload["activity_events"] == 2
    assert payload["unique_learners"] == 2
    quiz = payload["quizzes"][0]
    assert quiz["component_id"] == "risk-check"
    assert quiz["activity_events"] == 2
    assert quiz["unique_learners"] == 2
    assert quiz["publication_version"] == 1
    assert quiz["version_status"] == "current"
    assert quiz["first_attempt"] == {
        "evidence_type": "quiz_first_attempt",
        "sample_size": 2,
        "data_status": "insufficient_data",
        "rate": None,
    }
    assert quiz["options"] is None
    assert "attendance_split" not in quiz
    assert payload["learning_map"]["nodes"][0]["id"] == "risk"
    assert payload["learning_map"]["nodes"][0]["quiz_ids"] == ["risk-check"]
    assert payload["learning_map"]["nodes"][0]["gate_ids"] == ["risk-evidence-check"]
    assert payload["learning_map"]["gates"][0]["title"] == "Risk evidence gate"


def test_students_cannot_read_professor_analytics(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get(
        "/admin/courses/demo-course/lectures/lecture-01/analytics",
        headers=student_headers("student-a"),
    )

    assert response.status_code == 403


def test_lecture_analytics_reject_unpublished_canvas_context(tmp_path: Path) -> None:
    client = _client(tmp_path)

    summary = client.get(
        "/admin/courses/martius-ml/lectures/lecture-04/analytics",
        headers=professor_headers(),
    )

    assert summary.status_code == 409
    assert "Publish" in summary.json()["detail"]


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    configure_canvas_workspace(
        app,
        CanvasWorkspace(
            workspace_root=tmp_path / "workspaces",
            material_root=tmp_path / "materials",
        ),
    )
    write_course_workspace(
        app.state.canvas_workspace.course_media_root("demo-course"),
        CourseWorkspaceResult(
            course=Course(
                id="demo-course",
                title="Demo Course",
                professor="Prof. Demo",
                term="Sommer 2026",
            ),
            lectures=[
                Lecture(
                    id="lecture-01",
                    course_id="demo-course",
                    title="Risk lecture",
                    date=date(2026, 6, 1),
                )
            ],
            active_lecture_id="lecture-01",
        ),
    )
    publish_course_canvas(app.state.canvas_workspace, _canvas_document(tmp_path))
    return TestClient(app)


def _canvas_document(tmp_path: Path) -> CanvasDocument:
    return CanvasDocument(
        id="demo-course-lecture-01",
        course_id="demo-course",
        lecture_id="lecture-01",
        title="Risk lecture",
        source_kind="generated",
        source_ref="test source",
        workspace_path=str(tmp_path / "canvas" / "index.md"),
        sections=[
            CanvasSection(
                id="risk",
                title="Risk decisions",
                source_ref="test source",
                blocks=[
                    CanvasBlock(
                        id="risk-check",
                        type="component",
                        component_id="risk-check",
                        component_type="single_choice_quiz",
                        caption="Risk threshold check",
                        text="Which action minimizes expected risk?",
                        items=[
                            "Use the largest class prior.",
                            "Use posterior-weighted loss.",
                            "Ignore costs.",
                        ],
                        option_ids=["prior-only", "posterior-loss", "ignore-cost"],
                        answer_index=1,
                    ),
                    CanvasBlock(
                        id="risk-evidence-check",
                        type="checkpoint",
                        caption="Risk evidence gate",
                        text="Explain how posterior and loss determine the action.",
                    ),
                ],
            )
        ],
    )

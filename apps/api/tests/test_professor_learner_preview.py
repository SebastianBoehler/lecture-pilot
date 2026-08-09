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
from lecturepilot.professor_preview import professor_preview_user_id


PREVIEW_HEADER = {"X-LecturePilot-Learner-Preview": "professor"}


def test_professor_preview_persists_private_quiz_state_without_analytics(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    professor = {**professor_headers("prof-1"), **PREVIEW_HEADER}

    blocked = client.get(
        "/courses/demo-course/lectures/lecture-01/canvas",
        headers=professor_headers("prof-1"),
    )
    opened = client.get(
        "/courses/demo-course/lectures/lecture-01/canvas",
        headers=professor,
    )
    quiz = client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=professor,
        json={
            "attendance": "present",
            "attempt_id": "preview-risk-quiz-1",
            "block_id": "risk-quiz",
            "option_index": 1,
            "publication_version": 1,
        },
    )
    analytics = client.get(
        "/admin/courses/demo-course/lectures/lecture-01/analytics",
        headers=professor_headers("prof-1"),
    )
    managed_courses = client.get("/admin/courses", headers=professor_headers("prof-1"))

    assert blocked.status_code == 403
    assert opened.status_code == 200
    assert quiz.status_code == 200
    assert quiz.json()["correct"] is True
    assert analytics.json()["activity_events"] == 0
    assert managed_courses.json()[0]["published_lecture_ids"] == ["lecture-01"]

    preview_user_id = professor_preview_user_id("prof-1", "demo-course")
    layout = client.app.state.canvas_workspace.layout
    preview_root = layout.user_root(preview_user_id)
    assert preview_root.parent.parent == layout.root / "previews"
    assert (
        preview_root / "courses" / "demo-course" / "lectures" / "lecture-01" / "quizzes.json"
    ).exists()
    assert (
        not layout.user_lecture_root("student-1", "demo-course", "lecture-01")
        .joinpath("quizzes.json")
        .exists()
    )


def test_professor_preview_reset_only_clears_the_professor_sandbox(tmp_path: Path) -> None:
    client = _client(tmp_path)
    professor = {**professor_headers("prof-1"), **PREVIEW_HEADER}
    quiz = client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=professor,
        json={
            "attendance": "present",
            "attempt_id": "preview-risk-quiz-1",
            "block_id": "risk-quiz",
            "option_index": 1,
            "publication_version": 1,
        },
    )
    assert quiz.status_code == 200
    preview_user_id = professor_preview_user_id("prof-1", "demo-course")
    quiz_state = (
        client.app.state.canvas_workspace.layout.user_lecture_root(
            preview_user_id, "demo-course", "lecture-01"
        )
        / "quizzes.json"
    )
    assert quiz_state.exists()

    reset = client.post(
        "/courses/demo-course/learner-workspace/reset",
        headers=professor,
        json={"reset_canvas": True, "reset_course_memory": True, "reset_progress": True},
    )
    assert reset.status_code == 200
    assert not quiz_state.exists()
    assert not client.app.state.canvas_workspace.layout.user_memories_dir(preview_user_id).exists()


def test_professor_preview_readiness_progress_is_not_counted_as_a_learner(tmp_path: Path) -> None:
    client = _client(tmp_path)
    professor = {**professor_headers("prof-1"), **PREVIEW_HEADER}
    check = client.get("/courses/demo-course/exam-readiness", headers=professor)
    answers = [
        (
            {"question_id": question["id"], "selected_index": 1}
            if question["kind"] == "multiple_choice"
            else {"question_id": question["id"], "text": "Expected risk includes loss."}
        )
        for question in check.json()["questions"]
    ]

    attempt = client.post(
        "/courses/demo-course/exam-readiness/attempts",
        headers=professor,
        json={"answers": answers},
    )
    summary = client.get(
        "/admin/courses/demo-course/exam-readiness/summary",
        headers=professor_headers("prof-1"),
    )

    assert check.status_code == 200
    assert attempt.status_code == 200
    assert summary.json()["total_attempts"] == 0
    assert summary.json()["unique_learners"] == 0
    preview_user_id = professor_preview_user_id("prof-1", "demo-course")
    progress = (
        client.app.state.canvas_workspace.layout.user_course_root(
            preview_user_id,
            "demo-course",
        )
        / "progress.json"
    )
    assert progress.exists()


def test_student_cannot_request_professor_preview(tmp_path: Path) -> None:
    response = _client(tmp_path).get(
        "/courses/demo-course/lectures/lecture-01/canvas",
        headers={
            **student_headers("student-1", course_ids=["demo-course"]),
            **PREVIEW_HEADER,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Professor access is required."


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
                title="Demo course",
                professor="Professor Demo",
                term="Sommer 2026",
            ),
            lectures=[
                Lecture(
                    id="lecture-01",
                    course_id="demo-course",
                    title="Risk",
                    date=date(2026, 6, 1),
                )
            ],
            active_lecture_id="lecture-01",
        ),
    )
    publish_course_canvas(app.state.canvas_workspace, _document())
    return TestClient(app)


def _document() -> CanvasDocument:
    return CanvasDocument(
        id="demo-course-lecture-01",
        course_id="demo-course",
        lecture_id="lecture-01",
        title="Risk",
        source_kind="generated",
        source_ref="lecture-01.tex",
        workspace_path="course/canvas/index.md",
        sections=[
            CanvasSection(
                id="risk",
                title="Risk",
                blocks=[
                    CanvasBlock(
                        id="risk-quiz",
                        type="quiz",
                        text="Which quantity should be minimized?",
                        items=["Posterior", "Expected risk"],
                        answer_index=1,
                    )
                ],
            )
        ],
    )

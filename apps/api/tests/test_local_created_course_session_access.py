from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from canvas_workspace_fixtures import published_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture
from security_db_helpers import FakeUniversityAdapter, candidate, login


def test_local_enrolled_session_can_open_matching_created_workspace(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("LECTUREPILOT_ENV", "development")
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "dev")
    monkeypatch.setenv("LECTUREPILOT_DEMO_INCLUDE_CREATED_COURSES", "true")
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    app.state.tuebingen_adapter = FakeUniversityAdapter(
        courses_by_user={
            "student01": [
                candidate(
                    "alma",
                    "unit:nlp",
                    title="INFO4193 Natural Language Processing",
                )
            ]
        }
    )
    _write_workspace(app.state.canvas_workspace, "info4193-natural-language-processing")
    client = TestClient(app)

    login(client, "student01")
    courses = client.get("/courses")
    lectures = client.get("/courses/info4193-natural-language-processing/lectures")

    assert courses.status_code == 200
    assert {course["id"] for course in courses.json()} == {"info4193-natural-language-processing"}
    assert lectures.status_code == 200
    assert lectures.json()[0]["content_ready"] is True


def _write_workspace(workspace: CanvasWorkspace, course_id: str) -> None:
    result = CourseWorkspaceResult(
        course=Course(
            id=course_id,
            title="INFO4193 Natural Language Processing",
            professor="professor-demo",
            term="Sommer 2026",
        ),
        lectures=[
            Lecture(
                id="lecture-01",
                course_id=course_id,
                title="Introduction",
                date=date(2026, 4, 13),
            )
        ],
        active_lecture_id="lecture-01",
    )
    write_course_workspace(workspace.course_media_root(course_id), result)
    workspace.write_course_canvas(published_course_canvas(course_id, "lecture-01"))

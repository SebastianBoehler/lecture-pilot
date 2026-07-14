from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture
from auth_helpers import professor_headers, student_headers


def test_created_course_requires_enrollment(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _write_workspace(client, course_id="restricted-course")
    client.app.state.canvas_workspace.write_course_canvas(
        _document("restricted-course", "lecture-01")
    )

    visible = client.get("/courses", headers=student_headers(course_ids=("martius-ml",)))
    denied = client.get(
        "/courses/restricted-course/lectures",
        headers=student_headers(course_ids=("martius-ml",)),
    )
    enrolled = client.get(
        "/courses/restricted-course/lectures",
        headers=student_headers(course_ids=("restricted-course",)),
    )

    assert visible.status_code == 200
    assert "restricted-course" not in {course["id"] for course in visible.json()}
    assert denied.status_code == 200
    assert denied.json() == []
    assert enrolled.status_code == 200
    assert enrolled.json()[0]["lecture"]["id"] == "lecture-01"


def test_future_dynamic_lecture_is_locked_for_enrolled_student(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _write_workspace(client, course_id="future-course", lecture_date=date(2099, 1, 1))
    client.app.state.canvas_workspace.write_course_canvas(_document("future-course", "lecture-01"))
    student = student_headers(course_ids=("future-course",))

    lectures = client.get("/courses/future-course/lectures", headers=student)
    canvas = client.get(
        "/courses/future-course/lectures/lecture-01/canvas?user_id=student01",
        headers=student,
    )
    professor_canvas = client.get(
        "/courses/future-course/lectures/lecture-01/canvas?user_id=student01",
        headers=professor_headers(),
    )

    assert lectures.status_code == 200
    assert lectures.json()[0]["release_status"] == "scheduled"
    assert lectures.json()[0]["unlocked"] is False
    assert canvas.status_code == 403
    assert professor_canvas.status_code == 403


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    return TestClient(app)


def _write_workspace(
    client: TestClient,
    *,
    course_id: str,
    lecture_date: date = date(2026, 6, 1),
) -> None:
    workspace = CourseWorkspaceResult(
        course=Course(
            id=course_id,
            title="Restricted Course",
            professor="Prof. Demo",
            term="Sommer 2026",
        ),
        lectures=[
            Lecture(
                id="lecture-01",
                course_id=course_id,
                title="Restricted Lecture",
                date=lecture_date,
            )
        ],
        active_lecture_id="lecture-01",
    )
    write_course_workspace(
        client.app.state.canvas_workspace.course_media_root(course_id),
        workspace,
    )


def _document(course_id: str, lecture_id: str) -> CanvasDocument:
    return CanvasDocument(
        id=f"{course_id}-{lecture_id}",
        course_id=course_id,
        lecture_id=lecture_id,
        title="Restricted Lecture",
        source_kind="generated",
        source_ref="test",
        workspace_path="test/index.md",
        sections=[
            CanvasSection(
                id="intro",
                title="Intro",
                source_ref="test",
                blocks=[CanvasBlock(id="intro-p", type="paragraph", text="Published.")],
            )
        ],
    )

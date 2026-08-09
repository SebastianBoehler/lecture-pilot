from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from canvas_workspace_fixtures import publish_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.lecture_access_models import (
    CourseAccessPolicy,
    LectureAccessRule,
    PublicationMode,
)
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture
from test_asset_auth import _document


def test_course_asset_must_be_referenced_by_the_authorized_lecture(tmp_path: Path) -> None:
    course_id = "asset-access-course"
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    layout = app.state.canvas_workspace.layout
    uploads = layout.course_uploads_dir(course_id)
    uploads.mkdir(parents=True)
    for name in ("released.png", "private.png", "unreferenced.png"):
        (uploads / name).write_bytes(b"\x89PNG\r\n")
    write_course_workspace(
        layout.course_root(course_id),
        CourseWorkspaceResult(
            course=Course(
                id=course_id, title="Asset access", professor="Professor", term="Sommer 2026"
            ),
            lectures=[
                Lecture(
                    id="lecture-released",
                    course_id=course_id,
                    title="Released",
                    date=date(2020, 1, 1),
                ),
                Lecture(
                    id="lecture-private",
                    course_id=course_id,
                    title="Private",
                    date=date(2020, 1, 1),
                    access_override=LectureAccessRule(
                        audience=CourseAccessPolicy.INSTRUCTORS_ONLY,
                        publication_mode=PublicationMode.ON_LECTURE_DATE,
                    ),
                ),
            ],
            active_lecture_id="lecture-released",
        ),
    )
    publish_course_canvas(
        app.state.canvas_workspace,
        _document(course_id, "lecture-released", asset_path="released.png"),
    )
    publish_course_canvas(
        app.state.canvas_workspace,
        _document(course_id, "lecture-private", asset_path="private.png"),
    )
    client = TestClient(app)
    student = student_headers("student01", course_ids=[course_id])
    released_url = f"/course-assets/{course_id}/lecture-released"

    assert client.get(f"{released_url}/released.png", headers=student).status_code == 200
    assert client.get(f"{released_url}/private.png", headers=student).status_code == 404
    assert (
        client.get(
            f"/course-assets/{course_id}/lecture-private/private.png", headers=student
        ).status_code
        == 404
    )
    assert (
        client.get(f"{released_url}/unreferenced.png", headers=professor_headers()).status_code
        == 200
    )

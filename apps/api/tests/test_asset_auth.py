from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture
from lecturepilot.professor_preview import professor_preview_user_id


def test_course_asset_requires_authentication(tmp_path: Path) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    asset_path = (
        app.state.canvas_workspace.layout.course_uploads_dir("martius-ml") / "figures" / "risk.png"
    )
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"\x89PNG\r\n")
    client = TestClient(app)
    url = "/course-assets/martius-ml/lecture-03/figures/risk.png"

    assert client.get(url).status_code == 401
    response = client.get(url, headers=student_headers("student01"))

    assert response.status_code == 200
    assert response.content.startswith(b"\x89PNG")


def test_professor_preview_asset_is_private_to_its_owner(tmp_path: Path) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    layout = app.state.canvas_workspace.layout
    preview_id = professor_preview_user_id("prof-1", "martius-ml")
    preview_key = layout.user_key(preview_id)
    asset = (
        layout.user_canvas_dir(preview_id, "martius-ml", "lecture-01")
        / "student-assets"
        / "preview.png"
    )
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"\x89PNG\r\n")
    client = TestClient(app)
    url = f"/workspace-assets/martius-ml/lecture-01/{preview_key}/student-assets/preview.png"

    owner = client.get(url, headers=professor_headers("prof-1"))
    other_professor = client.get(url, headers=professor_headers("prof-2"))
    student = client.get(
        url,
        headers=student_headers("student-1", course_ids=["martius-ml"]),
    )

    assert owner.status_code == 200
    assert owner.content.startswith(b"\x89PNG")
    assert other_professor.status_code == 403
    assert student.status_code == 403


def test_course_asset_uses_scheduled_source_directory(tmp_path: Path) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    layout = app.state.canvas_workspace.layout
    source_dir = layout.course_uploads_dir("martius-ml") / "uploads" / "course-folder"
    source_dir.mkdir(parents=True)
    (source_dir / "Lecture01-eng.tex").write_text("lecture", encoding="utf-8")
    slide = source_dir / "generated-slides" / "lecture-01" / "slides" / "slide-001.png"
    slide.parent.mkdir(parents=True)
    slide.write_bytes(b"\x89PNG\r\n")
    write_course_workspace(
        layout.course_root("martius-ml"),
        CourseWorkspaceResult(
            course=Course(
                id="martius-ml",
                title="Nested course",
                professor="Professor",
                term="Sommer 2026",
            ),
            lectures=[
                Lecture(
                    id="lecture-01",
                    course_id="martius-ml",
                    title="Introduction",
                    date="2026-04-14",
                    material_path="uploads/course-folder/Lecture01-eng.tex",
                )
            ],
            active_lecture_id="lecture-01",
        ),
    )
    client = TestClient(app)

    response = client.get(
        "/course-assets/martius-ml/lecture-01/generated-slides/lecture-01/slides/slide-001.png",
        headers=student_headers("student01"),
    )

    assert response.status_code == 200
    assert response.content.startswith(b"\x89PNG")

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.lecture_access_models import (
    CourseAccessPolicy,
    LectureAccessRule,
    PublicationMode,
)
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture
from lecturepilot.professor_preview import professor_preview_user_id


def test_normalized_course_asset_requires_authentication(tmp_path: Path) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    asset_path = (
        app.state.canvas_workspace.layout.course_normalized_dir("martius-ml")
        / "generated-slides"
        / "risk.png"
    )
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"\x89PNG\r\n")
    app.state.canvas_workspace.write_course_canvas(
        _document("martius-ml", "lecture-03", asset_path="generated-slides/risk.png")
    )
    client = TestClient(app)
    url = "/course-assets/martius-ml/lecture-03/generated-slides/risk.png"

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
    app.state.canvas_workspace.write_course_canvas(_document("martius-ml", "lecture-01"))
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
    slide.write_bytes(b"scheduled lecture slide")
    relative_slide = "generated-slides/lecture-01/slides/slide-001.png"
    for generic_root in (
        layout.course_normalized_dir("martius-ml"),
        layout.course_uploads_dir("martius-ml"),
    ):
        generic_slide = generic_root / relative_slide
        generic_slide.parent.mkdir(parents=True, exist_ok=True)
        generic_slide.write_bytes(b"generic shadow")
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
    app.state.canvas_workspace.write_course_canvas(
        _document(
            "martius-ml",
            "lecture-01",
            asset_path=relative_slide,
        )
    )
    client = TestClient(app)

    response = client.get(
        f"/course-assets/martius-ml/lecture-01/{relative_slide}",
        headers=student_headers("student01"),
    )

    assert response.status_code == 200
    assert response.content == b"scheduled lecture slide"


def test_course_asset_resolves_legacy_graphicspath_reference(tmp_path: Path, monkeypatch) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    layout = app.state.canvas_workspace.layout
    source_dir = layout.course_uploads_dir("martius-ml") / "uploads" / "course-folder"
    source_dir.mkdir(parents=True)
    (source_dir / "Lecture02.tex").write_text("lecture", encoding="utf-8")
    figure = source_dir / "images" / "examples" / "mnistExamples.png"
    figure.parent.mkdir(parents=True)
    figure.write_bytes(b"scheduled graphicspath image")
    for generic_root in (
        layout.course_normalized_dir("martius-ml"),
        layout.course_uploads_dir("martius-ml"),
    ):
        generic_figure = generic_root / "examples" / "mnistExamples.png"
        generic_figure.parent.mkdir(parents=True, exist_ok=True)
        generic_figure.write_bytes(b"generic shadow")
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
                    id="lecture-02",
                    course_id="martius-ml",
                    title="Generalization",
                    date="2026-04-21",
                    material_path="uploads/course-folder/Lecture02.tex",
                )
            ],
            active_lecture_id="lecture-02",
        ),
    )
    app.state.canvas_workspace.write_course_canvas(
        _document(
            "martius-ml",
            "lecture-02",
            asset_path="examples/mnistExamples.png",
        )
    )

    def reject_recursive_scan(*_args, **_kwargs):
        raise AssertionError("scheduled source lookup must not scan every uploaded file")

    monkeypatch.setattr("lecturepilot.canvas_asset_store.WorkspaceFS.files", reject_recursive_scan)
    response = TestClient(app).get(
        "/course-assets/martius-ml/lecture-02/examples/mnistExamples.png",
        headers=student_headers("student01"),
    )

    assert response.status_code == 200
    assert response.content == b"scheduled graphicspath image"


def test_course_asset_must_be_referenced_by_the_authorized_lecture(tmp_path: Path) -> None:
    course_id = "asset-access-course"
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
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
                id=course_id,
                title="Asset access",
                professor="Professor",
                term="Sommer 2026",
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
    app.state.canvas_workspace.write_course_canvas(
        _document(course_id, "lecture-released", asset_path="released.png")
    )
    app.state.canvas_workspace.write_course_canvas(
        _document(course_id, "lecture-private", asset_path="private.png")
    )
    client = TestClient(app)
    student = student_headers("student01", course_ids=[course_id])
    released_url = f"/course-assets/{course_id}/lecture-released"

    assert client.get(f"{released_url}/released.png", headers=student).status_code == 200
    assert client.get(f"{released_url}/private.png", headers=student).status_code == 404
    assert (
        client.get(
            f"/course-assets/{course_id}/lecture-private/private.png",
            headers=student,
        ).status_code
        == 404
    )
    assert (
        client.get(f"{released_url}/unreferenced.png", headers=professor_headers()).status_code
        == 200
    )


def _document(
    course_id: str,
    lecture_id: str,
    *,
    asset_path: str | None = None,
) -> CanvasDocument:
    blocks = (
        [CanvasBlock(id="intro-asset", type="asset", asset_path=asset_path)]
        if asset_path
        else [CanvasBlock(id="intro-p", type="paragraph", text="Published.")]
    )
    return CanvasDocument(
        id=f"{course_id}-{lecture_id}",
        course_id=course_id,
        lecture_id=lecture_id,
        title="Published lecture",
        source_kind="generated",
        source_ref="test",
        workspace_path="test/index.md",
        sections=[
            CanvasSection(
                id="intro",
                title="Intro",
                source_ref="test",
                blocks=blocks,
            )
        ],
    )

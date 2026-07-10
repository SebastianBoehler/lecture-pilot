from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_builder_source import course_builder_source_document
from lecturepilot.source_bundle import scan_source_bundle


def test_nested_markdown_sources_follow_applied_lecture_schedule(tmp_path: Path) -> None:
    client = _client(tmp_path)
    paths = (
        "uploads/course/Lecture 1 - Foundations/topic.md",
        "uploads/course/Lecture 2 - Models/topic.md",
    )
    _create_full_course(client, paths)
    _upload(client, paths[0], b"# Lecture One\n\nOnly lecture one explains foundations clearly.")
    _upload(
        client, paths[1], b"# Lecture Two\n\nOnly lecture two explains model selection clearly."
    )

    first = course_builder_source_document(client.app, "partitioned-course", "lecture-01")
    second = course_builder_source_document(client.app, "partitioned-course", "lecture-02")

    assert first.source_ref == paths[0]
    assert [section.title for section in first.sections] == ["Lecture One"]
    assert second.source_ref == paths[1]
    assert [section.title for section in second.sections] == ["Lecture Two"]


def test_same_named_nested_latex_sources_use_their_lecture_folders(tmp_path: Path) -> None:
    client = _client(tmp_path)
    paths = (
        "uploads/course/Lecture 1 - Foundations/slides.tex",
        "uploads/course/Lecture 2 - Models/slides.tex",
    )
    _create_full_course(client, paths)
    _upload(client, paths[0], _latex("Lecture One", "FOUNDATION-MARKER"))
    _upload(client, paths[1], _latex("Lecture Two", "MODEL-MARKER"))

    first = course_builder_source_document(client.app, "partitioned-course", "lecture-01")
    second = course_builder_source_document(client.app, "partitioned-course", "lecture-02")

    assert [section.title for section in first.sections] == ["Lecture One"]
    assert [section.title for section in second.sections] == ["Lecture Two"]
    assert first.source_ref == paths[0]
    assert second.source_ref == paths[1]


def test_rendered_pdf_slides_are_not_reindexed_as_professor_sources(tmp_path: Path) -> None:
    client = _client(tmp_path)
    path = "uploads/course/Lecture 1 - Foundations/slides.pdf"
    _create_full_course(client, (path,))
    _upload(client, path, _pdf("Grounded PDF lecture evidence for students."))

    document = course_builder_source_document(client.app, "partitioned-course", "lecture-01")

    workspace = client.app.state.canvas_workspace
    uploads = workspace.layout.course_uploads_dir("partitioned-course")
    normalized = workspace.layout.course_normalized_dir("partitioned-course")
    slide_paths = [
        block.asset_path
        for section in document.sections
        for block in section.blocks
        if block.asset_path and block.asset_path.startswith("generated-slides/")
    ]
    assert slide_paths
    assert all((normalized / path).exists() for path in slide_paths)
    assert not (uploads / "generated-slides").exists()
    assert [item.path for item in scan_source_bundle(uploads)] == [path]


def test_corrupt_pdf_is_rejected_before_it_reaches_the_source_index(tmp_path: Path) -> None:
    client = _client(tmp_path)
    path = "Lecture 1/corrupt.pdf"
    _create_full_course(client, (path,))
    response = client.post(
        "/admin/courses/partitioned-course/materials",
        data={"path": path},
        files={"file": (Path(path).name, b"not a PDF", "application/pdf")},
        headers=professor_headers(),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File contents do not match the requested file type."


def test_discovered_seeded_lecture_uses_the_same_authorization_catalog(tmp_path: Path) -> None:
    client = _client(tmp_path)
    material_root = client.app.state.canvas_workspace.material_root
    for number in range(1, 5):
        path = material_root / f"Lecture{number:02d}-eng.tex"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_latex(f"Lecture {number}", f"LECTURE-{number}"))

    response = client.get(
        "/courses/martius-ml/lectures/lecture-04/canvas/publication",
        headers=student_headers("student01"),
    )

    assert response.status_code == 200
    assert response.json()["published"] is False


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    return TestClient(app)


def _create_full_course(client: TestClient, paths: tuple[str, ...]) -> None:
    response = client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Partitioned Course",
            "target": "full-course",
            "lectures": [
                {
                    "number": f"{index:02d}",
                    "title": f"Lecture {index}",
                    "date": f"2026-10-{index + 10:02d}",
                    "material_path": path,
                }
                for index, path in enumerate(paths, start=1)
            ],
        },
        headers=professor_headers(),
    )
    assert response.status_code == 200


def _upload(client: TestClient, path: str, content: bytes) -> None:
    response = client.post(
        "/admin/courses/partitioned-course/materials",
        data={"path": path},
        files={"file": (Path(path).name, content)},
        headers=professor_headers(),
    )
    assert response.status_code == 200


def _latex(title: str, marker: str) -> bytes:
    return f"\\begin{{frame}}{{{title}}}{marker} contains useful teaching evidence.\\end{{frame}}".encode()


def _pdf(text: str) -> bytes:
    import fitz

    document = fitz.open()
    page = document.new_page(width=320, height=160)
    page.insert_text((24, 72), text)
    payload = document.tobytes()
    document.close()
    return payload

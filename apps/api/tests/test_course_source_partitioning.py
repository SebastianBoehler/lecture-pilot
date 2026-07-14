from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from canvas_workspace_fixtures import published_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_builder_source import course_builder_source_document
from lecturepilot.lecture_source_manifest import write_lecture_source_manifest
from lecturepilot.source_index import refresh_course_source_index
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


def test_tex_only_lecture_uses_compiled_slide_previews(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path)
    path = "Lecture01.tex"
    _create_full_course(client, (path,))
    _upload(client, path, _latex("Lecture One", "FOUNDATION-MARKER"))

    def compile_deck(**kwargs) -> Path:
        output = kwargs["output_root"] / "compiled-latex/lecture-01/hash/Lecture01-hash.pdf"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(_pdf("Compiled slide preview"))
        return output

    monkeypatch.setattr("lecturepilot.course_builder_source.compile_latex_deck", compile_deck)

    document = course_builder_source_document(client.app, "partitioned-course", "lecture-01")

    slide_paths = [
        block.asset_path
        for section in document.sections
        for block in section.blocks
        if block.asset_path and block.asset_path.startswith("generated-slides/")
    ]
    assert len(slide_paths) == 1
    assert slide_paths[0].startswith("generated-slides/lecture-01/Lecture01-hash-")
    assert slide_paths[0].endswith("/slide-001.png")
    assert document.warnings == []
    uploads = client.app.state.canvas_workspace.layout.course_uploads_dir("partitioned-course")
    assert [item.path for item in scan_source_bundle(uploads)] == [path]


def test_tex_compile_failure_keeps_text_canvas_and_adds_actionable_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lecturepilot.latex_compilation_client import LatexCompilationError

    client = _client(tmp_path)
    path = "Lecture01.tex"
    _create_full_course(client, (path,))
    _upload(client, path, _latex("Lecture One", "FOUNDATION-MARKER"))

    def fail_compile(**kwargs) -> Path:
        raise LatexCompilationError("private compiler detail")

    monkeypatch.setattr("lecturepilot.course_builder_source.compile_latex_deck", fail_compile)

    document = course_builder_source_document(client.app, "partitioned-course", "lecture-01")

    assert [section.title for section in document.sections] == ["Lecture One"]
    assert document.warnings == [
        "Lecture 01 · Lecture01.tex: Original slide previews could not be created from "
        "LaTeX. The text canvas is ready. Upload a matching PDF or fix the LaTeX source, "
        "then regenerate."
    ]
    assert "private compiler detail" not in document.warnings[0]


def test_numbered_handout_pdf_skips_compilation_and_is_not_duplicated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path)
    paths = ("Lecture01.tex", "Lecture02.tex")
    _create_full_course(client, paths)
    _upload(client, paths[1], _latex("Lecture Two", "MODEL-MARKER"))
    _upload(client, "Lecture02-handout.pdf", _pdf("Authoritative uploaded slides"))

    def unexpected_compile(**kwargs) -> Path:
        raise AssertionError("matching PDF must prevent compilation")

    monkeypatch.setattr("lecturepilot.course_builder_source.compile_latex_deck", unexpected_compile)

    document = course_builder_source_document(client.app, "partitioned-course", "lecture-02")

    slide_paths = [
        block.asset_path
        for section in document.sections
        for block in section.blocks
        if block.asset_path and block.asset_path.startswith("generated-slides/")
    ]
    assert len(slide_paths) == 1
    assert slide_paths[0].startswith("generated-slides/lecture-02/Lecture02-handout-")
    assert slide_paths[0].endswith("/slide-001.png")
    assert document.warnings == []


def test_manifest_assigned_generic_pdf_is_authoritative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path)
    paths = ("Lecture01.tex", "Lecture02.tex")
    _create_full_course(client, paths)
    _upload(client, paths[1], _latex("Lecture Two", "MODEL-MARKER"))
    _upload(client, "week-two.pdf", _pdf("Explicitly assigned slides"))
    workspace = client.app.state.canvas_workspace
    index = refresh_course_source_index(
        course_id="partitioned-course",
        uploads_dir=workspace.layout.course_uploads_dir("partitioned-course"),
        index_path=workspace.layout.course_source_index_path("partitioned-course"),
    )
    write_lecture_source_manifest(
        workspace.layout.lecture_source_manifest_path("partitioned-course", "lecture-02"),
        course_id="partitioned-course",
        lecture_id="lecture-02",
        file_paths=[paths[1], "week-two.pdf"],
        source_index=index,
    )

    def unexpected_compile(**kwargs) -> Path:
        raise AssertionError("assigned PDF must prevent compilation")

    monkeypatch.setattr("lecturepilot.course_builder_source.compile_latex_deck", unexpected_compile)

    document = course_builder_source_document(client.app, "partitioned-course", "lecture-02")

    slide_paths = [
        block.asset_path
        for section in document.sections
        for block in section.blocks
        if block.asset_path and block.asset_path.startswith("generated-slides/")
    ]
    assert len(slide_paths) == 1
    assert "/week-two-" in slide_paths[0]
    assert document.warnings == []


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
    client.app.state.canvas_workspace.write_course_canvas(
        published_course_canvas("martius-ml", "lecture-04")
    )

    response = client.get(
        "/courses/martius-ml/lectures/lecture-04/canvas/publication",
        headers=student_headers("student01"),
    )

    assert response.status_code == 200
    assert response.json()["published"] is True


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

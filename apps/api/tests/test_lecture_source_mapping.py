from pathlib import Path

from lecturepilot.canvas_workspace import CanvasWorkspace


def test_imports_all_available_demo_lecture_sources(tmp_path: Path) -> None:
    material_root = _write_materials(tmp_path)
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )

    documents = [
        workspace.read_document(course_id="martius-ml", lecture_id=lecture_id, user_id="student01")
        for lecture_id in ("lecture-01", "lecture-02", "lecture-03")
    ]

    assert [document.source_ref for document in documents] == [
        "Lecture01-eng.tex",
        "Lecture02-eng.tex",
        "Lecture03-eng.tex",
    ]
    assert [document.title for document in documents] == [
        "Introduction",
        "Linear Models and Generalization",
        "Bayesian Decision Theory",
    ]
    assert all(document.sections for document in documents)
    assert documents[1].sections[0].title == "Linear model recap"


def test_uploaded_latex_matches_requested_lecture_number_beyond_seeded_map(tmp_path: Path) -> None:
    material_root = tmp_path / "course"
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )
    for source_name, title in (
        ("Lecture01-eng.tex", "Wrong introduction"),
        ("nested/Lecture05-eng.tex", "Correct lecture five"),
    ):
        path = workspace.course_upload_path(course_id="martius-ml", path=source_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_latex_source(title, "Requested lecture content"), encoding="utf-8")

    document = workspace.source_document(
        course_id="martius-ml",
        lecture_id="lecture-05",
        workspace_path="published/index.md",
    )

    assert document.source_ref == "Lecture05-eng.tex"
    assert document.title == "Correct lecture five"


def _write_materials(tmp_path: Path) -> Path:
    material_root = tmp_path / "course"
    material_root.mkdir()
    for source_name, title, frame_title in (
        ("Lecture01-eng.tex", "Introduction", "Course setup"),
        ("Lecture02-eng.tex", "Linear Models and Generalization", "Linear model recap"),
        ("Lecture03-eng.tex", "Bayesian Decision Theory", "Bayesian Decision Theory: The Aim"),
    ):
        (material_root / source_name).write_text(
            _latex_source(title, frame_title),
            encoding="utf-8",
        )
    return material_root


def _latex_source(title: str, frame_title: str) -> str:
    return rf"""
\mytitle[6 May, 2026]{{1}}{{{title}}}
\begin{{frame}}{{{frame_title}}}
This lecture has enough source text to become a canvas section.
\end{{frame}}
"""

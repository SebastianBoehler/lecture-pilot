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


def _write_materials(tmp_path: Path) -> Path:
    material_root = tmp_path / "course"
    material_root.mkdir()
    for source_name, title, frame_title in (
        ("Lecture01-eng.tex", "Introduction", "Course setup"),
        ("Lecture02-eng.tex", "Linear Models and Generalization", "Linear model recap"),
        ("Lecture03-eng.tex", "Bayesian Decision Theory", "Bayesian Decision Theory: The Aim"),
    ):
        (material_root / source_name).write_text(
            rf"""
\mytitle[6 May, 2026]{{1}}{{{title}}}
\begin{{frame}}{{{frame_title}}}
This lecture has enough source text to become a canvas section.
\end{{frame}}
""",
            encoding="utf-8",
        )
    return material_root

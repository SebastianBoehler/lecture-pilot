from pathlib import Path

from lecturepilot.source_bundle import scan_source_bundle


def test_source_bundle_scans_professor_material_types(tmp_path: Path) -> None:
    root = tmp_path / "course"
    _write(root / "Lecture03-eng.tex")
    _write(root / "Lecture03-eng.md")
    _write(root / "images" / "Ch3" / "diagram.pdf")
    _write(root / "images" / "Ch3" / "figure.png")
    _write(root / "videos" / "demo.mp4")
    _write(root / "code" / "notebook.ipynb")
    _write(root / "code" / "demo.py")
    _write(root / "canvas" / "lectures" / "lecture-03" / "index.md")
    _write(root / ".git" / "HEAD")
    _write(root / ".lecturepilot-previews" / "preview.png")

    files = scan_source_bundle(root)

    assert [(item.path, item.kind) for item in files] == [
        ("Lecture03-eng.md", "markdown"),
        ("Lecture03-eng.tex", "latex"),
        ("code/demo.py", "code"),
        ("code/notebook.ipynb", "notebook"),
        ("images/Ch3/diagram.pdf", "pdf"),
        ("images/Ch3/figure.png", "image"),
        ("videos/demo.mp4", "video"),
    ]


def _write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("demo", encoding="utf-8")

from pathlib import Path

from lecturepilot.canvas_workspace import CanvasWorkspace


def test_pdf_course_asset_preview_renders_png(tmp_path: Path) -> None:
    material_root = tmp_path / "course"
    image_dir = material_root / "images" / "Ch3"
    image_dir.mkdir(parents=True)
    _write_pdf(image_dir / "diagram.pdf")
    (material_root / "Lecture03-eng.tex").write_text("source", encoding="utf-8")
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )

    preview = workspace.asset_preview_path(lecture_id="lecture-03", asset_path="Ch3/diagram.pdf")

    assert preview.suffix == ".png"
    assert preview.exists()
    assert preview.read_bytes().startswith(b"\x89PNG")


def _write_pdf(path: Path) -> None:
    import fitz

    document = fitz.open()
    page = document.new_page(width=120, height=80)
    page.insert_text((20, 40), "diagram")
    document.save(path)
    document.close()

from pathlib import Path

from lecturepilot.pdf_slide_assets import render_pdf_slide_blocks


def test_render_pdf_slide_blocks_creates_course_asset_pngs(tmp_path: Path) -> None:
    source_root = tmp_path / "uploads"
    source_root.mkdir()
    pdf_path = source_root / "lecture-01.pdf"
    _write_pdf(pdf_path, ["slide one", "slide two"])

    blocks = render_pdf_slide_blocks(
        pdf_path=pdf_path,
        source_root=source_root,
        course_id="demo-course",
        lecture_id="lecture-01",
        source_ref="lecture-01.pdf",
    )

    assert [block.id for block in blocks] == [
        "lecture-01-original-slide-001",
        "lecture-01-original-slide-002",
    ]
    assert blocks[0].asset_path == "generated-slides/lecture-01/lecture-01/slide-001.png"
    assert blocks[0].asset_url.endswith("generated-slides/lecture-01/lecture-01/slide-001.png")
    assert blocks[0].caption == "Original slide 1 from lecture-01.pdf"
    assert (source_root / blocks[0].asset_path).read_bytes().startswith(b"\x89PNG")
    assert (source_root / blocks[1].asset_path).read_bytes().startswith(b"\x89PNG")


def _write_pdf(path: Path, labels: list[str]) -> None:
    import fitz

    document = fitz.open()
    for label in labels:
        page = document.new_page(width=160, height=90)
        page.insert_text((20, 45), label)
    document.save(path)
    document.close()

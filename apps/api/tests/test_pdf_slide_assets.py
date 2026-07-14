import hashlib
from pathlib import Path

from lecturepilot.pdf_slide_assets import MAX_RENDERED_SLIDES, render_pdf_slide_blocks


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
    fingerprint = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    slide_root = f"generated-slides/lecture-01/lecture-01-{fingerprint}"

    assert [block.id for block in blocks] == [
        "lecture-01-original-slide-001",
        "lecture-01-original-slide-002",
    ]
    assert blocks[0].asset_path == f"{slide_root}/slide-001.png"
    assert blocks[0].asset_url.endswith(f"{slide_root}/slide-001.png")
    assert blocks[0].caption == "Original slide 1 from lecture-01.pdf"
    assert (source_root / blocks[0].asset_path).read_bytes().startswith(b"\x89PNG")
    assert (source_root / blocks[1].asset_path).read_bytes().startswith(b"\x89PNG")


def test_render_pdf_slide_blocks_versions_assets_when_same_path_is_replaced(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "uploads"
    source_root.mkdir()
    pdf_path = source_root / "lecture-01.pdf"
    _write_pdf(pdf_path, ["original slide content"])

    original = render_pdf_slide_blocks(
        pdf_path=pdf_path,
        source_root=source_root,
        course_id="demo-course",
        lecture_id="lecture-01",
        source_ref="lecture-01.pdf",
    )[0]
    original_png = (source_root / original.asset_path).read_bytes()

    pdf_path.unlink()
    _write_pdf(pdf_path, ["replacement content"])
    replacement = render_pdf_slide_blocks(
        pdf_path=pdf_path,
        source_root=source_root,
        course_id="demo-course",
        lecture_id="lecture-01",
        source_ref="lecture-01.pdf",
    )[0]
    replacement_png = (source_root / replacement.asset_path).read_bytes()

    assert replacement.asset_path != original.asset_path
    assert replacement.asset_url != original.asset_url
    assert replacement_png != original_png
    assert (source_root / original.asset_path).read_bytes() == original_png


def test_render_pdf_slide_blocks_samples_across_the_full_deck(tmp_path: Path) -> None:
    source_root = tmp_path / "uploads"
    source_root.mkdir()
    pdf_path = source_root / "long-lecture.pdf"
    page_count = MAX_RENDERED_SLIDES + 7
    _write_pdf(pdf_path, [f"slide {number}" for number in range(1, page_count + 1)])

    blocks = render_pdf_slide_blocks(
        pdf_path=pdf_path,
        source_root=source_root,
        course_id="demo-course",
        lecture_id="lecture-01",
        source_ref="long-lecture.pdf",
    )

    rendered_pages = [int((block.caption or "").split()[2]) for block in blocks]
    assert len(blocks) == MAX_RENDERED_SLIDES
    assert rendered_pages[0] == 1
    assert rendered_pages[-1] == page_count
    assert rendered_pages == sorted(set(rendered_pages))
    assert blocks[-1].asset_path.endswith(f"slide-{page_count:03}.png")
    assert (source_root / blocks[-1].asset_path).read_bytes().startswith(b"\x89PNG")


def _write_pdf(path: Path, labels: list[str]) -> None:
    import fitz

    document = fitz.open()
    for label in labels:
        page = document.new_page(width=160, height=90)
        page.insert_text((20, 45), label)
    document.save(path)
    document.close()

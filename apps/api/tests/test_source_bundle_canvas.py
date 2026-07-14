from pathlib import Path

from lecturepilot.pdf_slide_assets import MAX_RENDERED_SLIDES
from lecturepilot.source_bundle_canvas import MAX_PDF_PAGES, import_source_bundle_canvas


def test_source_bundle_canvas_imports_markdown_text_pdf_and_assets(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write(
        root / "notes" / "overview.md",
        "# Bayes Overview\n\nBayes updates prior beliefs from observed evidence.",
    )
    _write(
        root / "notes" / "context.txt",
        "Risk-sensitive decisions compare posterior beliefs with action costs.",
    )
    _write_pdf(
        root / "slides" / "decision.pdf",
        "PDF slide explains likelihood evidence and posterior risk.",
    )
    _write(root / "images" / "diagram.png", "\x89PNG\r\n", binary=True)
    _write(
        root / "images" / "diagram.png.json",
        '{"title":"Risk boundary diagram","description":"Shows posterior regions and costly errors."}',
    )
    _write(root / "videos" / "walkthrough.mp4", "\x00\x00\x00\x18ftypmp42", binary=True)
    _write(
        root / "videos" / "walkthrough.json",
        '{"title":"Professor walkthrough","tags":["bayes","risk"]}',
    )

    document = import_source_bundle_canvas(
        source_root=root,
        course_id="demo-course",
        lecture_id="lecture-01",
        workspace_path="planner/source.json",
    )

    assert document.source_kind == "markdown"
    assert document.source_ref == "notes/context.txt, notes/overview.md, slides/decision.pdf"
    section_titles = [section.title for section in document.sections]
    assert "Bayes Overview" in section_titles
    assert "Context" in section_titles
    assert "Decision" in section_titles
    assert any(
        "posterior risk" in block.text
        for section in document.sections
        for block in section.blocks
        if block.text
    )
    assets = [
        block for section in document.sections for block in section.blocks if block.type == "asset"
    ]
    asset_paths = {asset.asset_path for asset in assets}
    generated_slide = next(path for path in asset_paths if path.startswith("generated-slides/"))
    assert generated_slide.startswith("generated-slides/lecture-01/decision-")
    assert generated_slide.endswith("/slide-001.png")
    assert asset_paths - {generated_slide} == {"images/diagram.png", "slides/decision.pdf"}
    assert next(
        asset.caption for asset in assets if asset.asset_path == "images/diagram.png"
    ).startswith("Risk boundary diagram")
    assert assets[0].asset_url.startswith("/course-assets/demo-course/lecture-01/")
    videos = [
        block for section in document.sections for block in section.blocks if block.type == "video"
    ]
    assert [(video.asset_path, video.caption) for video in videos] == [
        ("videos/walkthrough.mp4", "Professor walkthrough - bayes, risk")
    ]


def test_pdf_source_bundle_adds_original_slide_assets(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write_pdf(
        root / "lecture-01.pdf",
        "Bayes rule updates prior beliefs after observing evidence.",
        "Decision risk compares posterior beliefs with action costs.",
    )

    document = import_source_bundle_canvas(
        source_root=root,
        course_id="demo-course",
        lecture_id="lecture-01",
        workspace_path="planner/source.json",
    )

    slide_blocks = [
        block
        for section in document.sections
        for block in section.blocks
        if block.asset_path and block.asset_path.startswith("generated-slides/")
    ]
    assert [block.caption for block in slide_blocks] == [
        "Original slide 1 from lecture-01.pdf",
        "Original slide 2 from lecture-01.pdf",
    ]


def test_tex_and_matching_pdf_create_one_slide_preview_set(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write(
        root / "Lecture02.tex",
        r"\begin{frame}{Regression}Regression predicts continuous target values from input features.\end{frame}",
    )
    _write_pdf(root / "Lecture02.pdf", "Regression predicts a continuous target.")

    document = import_source_bundle_canvas(
        source_root=root,
        course_id="demo-course",
        lecture_id="lecture-02",
        workspace_path="planner/source.json",
    )

    slide_paths = [
        block.asset_path
        for section in document.sections
        for block in section.blocks
        if block.asset_path and block.asset_path.startswith("generated-slides/")
    ]
    assert len(slide_paths) == 1
    assert slide_paths[0].startswith("generated-slides/lecture-02/Lecture02-")
    assert slide_paths[0].endswith("/slide-001.png")


def test_compiled_slide_pdf_is_visual_evidence_without_duplicate_pdf_text(
    tmp_path: Path,
) -> None:
    root = tmp_path / "bundle"
    derived = tmp_path / "normalized"
    _write(
        root / "Lecture02.tex",
        r"\begin{frame}{Regression}Regression predicts continuous target values from input features.\end{frame}",
    )
    compiled_pdf = derived / "compiled-latex" / "lecture-02" / "hash" / "Lecture02.pdf"
    _write_pdf(compiled_pdf, "Rendered preview text must not become duplicate source evidence.")

    document = import_source_bundle_canvas(
        source_root=root,
        course_id="demo-course",
        lecture_id="lecture-02",
        workspace_path="planner/source.json",
        derived_root=derived,
        compiled_slide_pdf=compiled_pdf,
        compiled_slide_source_ref="Lecture02.tex",
    )

    text = " ".join(
        block.text or ""
        for section in document.sections
        for block in section.blocks
        if block.type == "paragraph"
    )
    slides = [
        block
        for section in document.sections
        for block in section.blocks
        if block.asset_path and block.asset_path.startswith("generated-slides/")
    ]
    assert "duplicate source evidence" not in text
    assert [slide.caption for slide in slides] == ["Compiled slide 1 from Lecture02.tex"]


def test_pdf_source_bundle_samples_text_and_slides_across_the_full_deck(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    page_count = max(MAX_PDF_PAGES, MAX_RENDERED_SLIDES) + 7
    _write_pdf(
        root / "long-lecture.pdf",
        *[
            f"Page {number} explains a unique concept from this part of the lecture."
            for number in range(1, page_count + 1)
        ],
    )

    document = import_source_bundle_canvas(
        source_root=root,
        course_id="demo-course",
        lecture_id="lecture-01",
        workspace_path="planner/source.json",
    )

    section = next(item for item in document.sections if item.id == "long-lecture-pdf")
    paragraph_text = "\n".join(
        block.text or "" for block in section.blocks if block.type == "paragraph"
    )
    slide_captions = [
        block.caption or ""
        for block in section.blocks
        if block.asset_path and block.asset_path.startswith("generated-slides/")
    ]
    assert "[PDF page 1]" in paragraph_text
    assert f"[PDF page {page_count}]" in paragraph_text
    assert section.source_ref and section.source_ref.endswith(str(page_count))
    assert slide_captions[0] == "Original slide 1 from long-lecture.pdf"
    assert slide_captions[-1] == f"Original slide {page_count} from long-lecture.pdf"


def _write(path: Path, content: str, *, binary: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        path.write_bytes(content.encode("latin1"))
    else:
        path.write_text(content, encoding="utf-8")


def _write_pdf(path: Path, *texts: str) -> None:
    import fitz

    path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    for text in texts:
        page = document.new_page(width=320, height=160)
        page.insert_text((24, 72), text)
    document.save(path)
    document.close()

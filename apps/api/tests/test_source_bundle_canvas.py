from pathlib import Path

from lecturepilot.source_bundle_canvas import import_source_bundle_canvas


def test_source_bundle_canvas_imports_markdown_text_pdf_and_assets(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write(root / "notes" / "overview.md", "# Bayes Overview\n\nBayes updates prior beliefs from observed evidence.")
    _write(root / "notes" / "context.txt", "Risk-sensitive decisions compare posterior beliefs with action costs.")
    _write_pdf(root / "slides" / "decision.pdf", "PDF slide explains likelihood evidence and posterior risk.")
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
    assert any("posterior risk" in block.text for section in document.sections for block in section.blocks if block.text)
    assets = [block for section in document.sections for block in section.blocks if block.type == "asset"]
    assert {asset.asset_path for asset in assets} == {
        "generated-slides/lecture-01/decision/slide-001.png",
        "images/diagram.png",
        "slides/decision.pdf",
    }
    assert next(asset.caption for asset in assets if asset.asset_path == "images/diagram.png").startswith(
        "Risk boundary diagram"
    )
    assert assets[0].asset_url.startswith("/course-assets/demo-course/lecture-01/")
    videos = [block for section in document.sections for block in section.blocks if block.type == "video"]
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

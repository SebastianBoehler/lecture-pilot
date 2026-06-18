from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_slide_interleaving import interleave_original_slides


def test_interleave_original_slides_matches_page_refs() -> None:
    source = _document("source", [_section("source-pdf", [_slide(1), _slide(2), _slide(3)])])
    planned = _document(
        "generated",
        [
            _section("posterior", [_paragraph("Bayes update")], source_ref="lecture.pdf pages 2-3"),
            _section("risk", [_paragraph("Risk decision")], source_ref="lecture.pdf page 1"),
        ],
    )

    interleaved = interleave_original_slides(planned, source)

    assert interleaved.sections[0].blocks[0].asset_path.endswith("slide-002.png")
    assert interleaved.sections[1].blocks[0].asset_path.endswith("slide-001.png")
    assert interleaved.sections[0].blocks[1].text == "Bayes update"


def test_interleave_original_slides_distributes_without_page_refs() -> None:
    source = _document("source", [_section("source-pdf", [_slide(1), _slide(2), _slide(3)])])
    planned = _document(
        "generated",
        [
            _section("topic-1", [_paragraph("First")]),
            _section("topic-2", [_paragraph("Second")]),
        ],
    )

    interleaved = interleave_original_slides(planned, source)

    assert interleaved.sections[0].blocks[0].asset_path.endswith("slide-001.png")
    assert interleaved.sections[1].blocks[0].asset_path.endswith("slide-003.png")


def _document(kind: str, sections: list[CanvasSection]) -> CanvasDocument:
    return CanvasDocument(
        id=f"demo-{kind}",
        course_id="demo-course",
        lecture_id="lecture-01",
        title="Demo",
        source_kind="generated" if kind == "generated" else "markdown",
        source_ref="lecture.pdf",
        workspace_path="canvas/index.md",
        sections=sections,
    )


def _section(section_id: str, blocks: list[CanvasBlock], source_ref: str | None = None) -> CanvasSection:
    return CanvasSection(id=section_id, title=section_id.title(), source_ref=source_ref, blocks=blocks)


def _paragraph(text: str) -> CanvasBlock:
    return CanvasBlock(id=f"{text.lower().replace(' ', '-')}-p", type="paragraph", text=text)


def _slide(number: int) -> CanvasBlock:
    return CanvasBlock(
        id=f"original-slide-{number:03}",
        type="asset",
        asset_path=f"generated-slides/lecture-01/lecture/slide-{number:03}.png",
        asset_url=f"/course-assets/demo-course/lecture-01/generated-slides/lecture-01/lecture/slide-{number:03}.png",
        caption=f"Original slide {number} from lecture.pdf",
    )

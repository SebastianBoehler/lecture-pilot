from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_slide_interleaving import interleave_original_slides


def test_interleave_original_slides_matches_pages_from_the_cited_pdf() -> None:
    source = _document(
        "source",
        [
            _section("lecture-pdf", [_slide(1), _slide(2), _slide(3)]),
            _section(
                "handout-pdf",
                [
                    _slide(1, "lecture-handout.pdf"),
                    _slide(2, "lecture-handout.pdf"),
                    _slide(3, "lecture-handout.pdf"),
                ],
            ),
        ],
    )
    planned = _document(
        "generated",
        [
            _section(
                "posterior",
                [_paragraph("Bayes update")],
                source_ref="lecture-handout.pdf pages 2-3",
            ),
            _section("risk", [_paragraph("Risk decision")], source_ref="lecture.pdf page 1"),
        ],
    )

    interleaved = interleave_original_slides(planned, source)

    assert _slide_captions(interleaved.sections[0]) == [
        "Original slide 2 from lecture-handout.pdf",
        "Original slide 3 from lecture-handout.pdf",
    ]
    assert interleaved.sections[1].blocks[0].asset_path.endswith("slide-001.png")
    assert interleaved.sections[0].blocks[1].text == "Bayes update"


def test_interleave_original_slides_distributes_exact_companion_pdf_without_using_frame_numbers() -> (
    None
):
    source = _document(
        "source",
        [
            _section(
                "source-pdf",
                [_slide(1), _slide(6), _slide(12), _slide(18), _slide(24), _slide(30)],
            )
        ],
    )
    planned = _document(
        "generated",
        [
            _section("topic-1", [_paragraph("First")], source_ref="lecture.tex frames 28-30"),
            _section("topic-2", [_paragraph("Second")], source_ref="lecture.tex frames 1-2"),
            _section("topic-3", [_paragraph("Third")], source_ref="lecture.tex frames 14-16"),
        ],
    )

    interleaved = interleave_original_slides(planned, source)

    assert [_slide_numbers(section) for section in interleaved.sections] == [
        [1, 6],
        [12, 18],
        [24, 30],
    ]


def test_interleave_original_slides_does_not_map_tex_frames_to_a_handout_pdf() -> None:
    source = _document(
        "source",
        [
            _section(
                "handout-pdf",
                [_slide(1, "lecture-handout.pdf"), _slide(2, "lecture-handout.pdf")],
            )
        ],
    )
    planned = _document(
        "generated",
        [_section("topic", [_paragraph("Explanation")], source_ref="lecture.tex frames 1-2")],
    )

    interleaved = interleave_original_slides(planned, source)

    assert _slide_captions(interleaved.sections[0]) == []
    assert interleaved.sections[0].blocks[0].text == "Explanation"


def test_interleave_compiled_tex_slides_across_tex_sections() -> None:
    source = _document(
        "source",
        [
            _section(
                "compiled-slides",
                [
                    _slide(1, "lecture.tex", label="Compiled"),
                    _slide(2, "lecture.tex", label="Compiled"),
                ],
            )
        ],
    )
    planned = _document(
        "generated",
        [
            _section("topic-1", [_paragraph("First")], source_ref="lecture.tex frames 1-2"),
            _section("topic-2", [_paragraph("Second")], source_ref="lecture.tex frames 3-4"),
        ],
    )

    interleaved = interleave_original_slides(planned, source)

    assert _slide_captions(interleaved.sections[0]) == ["Compiled slide 1 from lecture.tex"]
    assert _slide_captions(interleaved.sections[1]) == ["Compiled slide 2 from lecture.tex"]


def test_interleave_original_slides_does_not_duplicate_an_existing_asset() -> None:
    slides = [_slide(1), _slide(2), _slide(3)]
    source = _document("source", [_section("source-pdf", slides)])
    planned = _document(
        "generated",
        [
            _section(
                "topic",
                [slides[0], _paragraph("Explanation")],
                source_ref="lecture.tex frames 1-3",
            )
        ],
    )

    interleaved = interleave_original_slides(planned, source)

    assert _slide_numbers(interleaved.sections[0]) == [1, 2]
    assert (
        len({block.asset_path for block in interleaved.sections[0].blocks if block.asset_path}) == 2
    )


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


def _section(
    section_id: str, blocks: list[CanvasBlock], source_ref: str | None = None
) -> CanvasSection:
    return CanvasSection(
        id=section_id, title=section_id.title(), source_ref=source_ref, blocks=blocks
    )


def _paragraph(text: str) -> CanvasBlock:
    return CanvasBlock(id=f"{text.lower().replace(' ', '-')}-p", type="paragraph", text=text)


def _slide(number: int, source_ref: str = "lecture.pdf", *, label: str = "Original") -> CanvasBlock:
    source_stem = source_ref.removesuffix(".pdf")
    return CanvasBlock(
        id=f"{source_stem}-original-slide-{number:03}",
        type="asset",
        asset_path=f"generated-slides/lecture-01/{source_stem}/slide-{number:03}.png",
        asset_url=f"/course-assets/demo-course/lecture-01/generated-slides/lecture-01/{source_stem}/slide-{number:03}.png",
        caption=f"{label} slide {number} from {source_ref}",
    )


def _slide_captions(section: CanvasSection) -> list[str]:
    return [
        block.caption or ""
        for block in section.blocks
        if block.asset_path and block.asset_path.startswith("generated-slides/")
    ]


def _slide_numbers(section: CanvasSection) -> list[int]:
    return [int(caption.split()[2]) for caption in _slide_captions(section)]

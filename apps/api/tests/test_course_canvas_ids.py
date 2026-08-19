from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_ids import avoid_mirrored_section_ids, ensure_unique_block_ids


def test_renames_planned_sections_that_mirror_extracted_source_ids() -> None:
    source = _document(
        "source-slide-1",
        [CanvasBlock(id="source-slide-1-p-1", type="paragraph", text="Source text")],
    )
    planned = _document(
        "source-slide-1",
        [
            CanvasBlock(id="source-slide-1-p-1", type="paragraph", text="Planned teaching text"),
            CanvasBlock(
                id="custom-quiz", type="quiz", text="Check?", items=["A", "B"], answer_index=0
            ),
        ],
    )

    result = avoid_mirrored_section_ids(planned, source)

    assert result.sections[0].id == "learning-1-source-slide-1"
    assert result.sections[0].blocks[0].id == "learning-1-source-slide-1-p-1"
    assert result.sections[0].blocks[1].id == "custom-quiz"


def test_normalizes_duplicate_block_ids_across_and_within_sections() -> None:
    document = _document(
        "first",
        [
            CanvasBlock(id="shared", type="paragraph", text="First"),
            CanvasBlock(id="shared", type="paragraph", text="Second"),
        ],
    )
    document.sections.append(
        CanvasSection(
            id="second",
            title="Second",
            source_ref="Lecture03-eng.tex",
            blocks=[CanvasBlock(id="shared", type="paragraph", text="Third")],
        )
    )

    result = ensure_unique_block_ids(document)

    assert [block.id for section in result.sections for block in section.blocks] == [
        "shared",
        "shared-2",
        "shared-3",
    ]


def _document(section_id: str, blocks: list[CanvasBlock]) -> CanvasDocument:
    return CanvasDocument(
        id="martius-ml-lecture-03",
        course_id="martius-ml",
        lecture_id="lecture-03",
        title="Lecture",
        source_kind="latex",
        source_ref="Lecture03-eng.tex",
        workspace_path="index.md",
        sections=[
            CanvasSection(
                id=section_id, title="Section", source_ref="Lecture03-eng.tex", blocks=blocks
            )
        ],
    )

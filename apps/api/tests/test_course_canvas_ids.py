from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_ids import avoid_mirrored_section_ids


def test_renames_planned_sections_that_mirror_extracted_source_ids() -> None:
    source = _document(
        "source-slide-1",
        [CanvasBlock(id="source-slide-1-p-1", type="paragraph", text="Source text")],
    )
    planned = _document(
        "source-slide-1",
        [
            CanvasBlock(id="source-slide-1-p-1", type="paragraph", text="Planned teaching text"),
            CanvasBlock(id="custom-quiz", type="quiz", text="Check?", items=["A", "B"], answer_index=0),
        ],
    )

    result = avoid_mirrored_section_ids(planned, source)

    assert result.sections[0].id == "learning-1-source-slide-1"
    assert result.sections[0].blocks[0].id == "learning-1-source-slide-1-p-1"
    assert result.sections[0].blocks[1].id == "custom-quiz"


def _document(section_id: str, blocks: list[CanvasBlock]) -> CanvasDocument:
    return CanvasDocument(
        id="martius-ml-lecture-03",
        course_id="martius-ml",
        lecture_id="lecture-03",
        title="Lecture",
        source_kind="latex",
        source_ref="Lecture03-eng.tex",
        workspace_path="index.md",
        sections=[CanvasSection(id=section_id, title="Section", source_ref="Lecture03-eng.tex", blocks=blocks)],
    )

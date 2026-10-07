from __future__ import annotations

from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_validation import (
    source_topic_sections,
    validate_planned_document,
)
from lecturepilot.latex_canvas_importer import import_latex_canvas


def test_validation_does_not_enforce_a_section_or_character_quota() -> None:
    validate_planned_document(_generated_document(1), _source_document(10))


def test_asset_only_outline_section_does_not_inflate_fallback_topic_count() -> None:
    source = _source_document(7)
    source.sections.append(
        CanvasSection(
            id="original-slides",
            title="Original slides",
            source_ref="Lecture.pdf",
            blocks=[
                CanvasBlock(
                    id="slide-1",
                    type="asset",
                    asset_path="generated-slides/slide-001.png",
                )
            ],
        )
    )

    assert len(source_topic_sections(source)) == 7


def test_latex_study_groups_keep_richer_paragraph_list_and_formula_evidence(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "Lecture08.tex"
    paragraphs = "\\pause\n".join(
        f"Paragraph {index} explains a distinct mechanism with enough words for study."
        for index in range(1, 7)
    )
    items = "\n".join(
        rf"\item Evidence item {index} explains a distinct learning step." for index in range(1, 21)
    )
    formulas = "\n".join(rf"\[ x_{{{index}}} = {index} \]" for index in range(1, 8))
    first_frames = rf"""
\begin{{frame}}{{Rich topic one}}
{paragraphs}
\begin{{itemize}}
{items}
\end{{itemize}}
{formulas}
\end{{frame}}
\begin{{frame}}{{Rich topic two}}
This second frame adds another substantive explanation for the same topic group.
\end{{frame}}
"""
    remaining_frames = "\n".join(
        rf"\begin{{frame}}{{Topic {index}}}This frame explains topic {index} with enough learning words.\end{{frame}}"
        for index in range(3, 9)
    )
    source_path.write_text(first_frames + remaining_frames, encoding="utf-8")

    document = import_latex_canvas(
        source_path=source_path,
        material_root=tmp_path,
        course_id="course",
        lecture_id="lecture-08",
        workspace_path="canvas/index.md",
    )
    first_group = document.sections[0]

    assert len([block for block in first_group.blocks if block.type == "paragraph"]) == 4
    assert len(next(block for block in first_group.blocks if block.type == "list").items) == 16
    assert len([block for block in first_group.blocks if block.type == "math"]) == 5
    assert any(block.id.endswith("derivation-note") for block in first_group.blocks)


def _source_document(section_count: int, *, text_size: int = 80) -> CanvasDocument:
    sections = [
        CanvasSection(
            id=f"source-{index}",
            title=f"Source topic {index}",
            source_ref=f"frames {index}",
            blocks=[
                CanvasBlock(
                    id=f"source-{index}-paragraph",
                    type="paragraph",
                    text=(f"Evidence {index} " + "mechanism " * text_size).strip(),
                )
            ],
        )
        for index in range(1, section_count + 1)
    ]
    return CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="latex",
        source_ref="Lecture.tex",
        workspace_path="canvas/index.md",
        sections=sections,
    )


def _dense_section(*, text_size: int, block_count: int) -> CanvasSection:
    return CanvasSection(
        id="dense",
        title="Dense source topic",
        source_ref="frames 1-8",
        blocks=[
            CanvasBlock(
                id=f"dense-{index}",
                type="paragraph",
                text=(f"Block {index} " + "evidence " * text_size).strip(),
            )
            for index in range(1, block_count + 1)
        ],
    )


def _generated_document(section_count: int) -> CanvasDocument:
    sections = []
    for index in range(1, section_count + 1):
        blocks = [
            CanvasBlock(
                id=f"learning-{index}-paragraph-{block_index}",
                type="paragraph",
                text=(
                    f"Detailed mechanism {index}.{block_index} explains the source concept, "
                    "its constraints, a concrete consequence, and a failure mode in enough "
                    "depth for independent study and later transfer practice."
                ),
            )
            for block_index in range(1, 5)
        ]
        blocks.append(
            CanvasBlock(
                id=f"learning-{index}-check",
                type="checkpoint",
                text=(
                    f"Explain how the mechanism for topic {index} follows from the evidence "
                    "and identify one failure mode."
                ),
            )
        )
        if index == 2 or index == section_count:
            blocks.append(
                CanvasBlock(
                    id=f"quiz-{index}",
                    type="quiz",
                    text="Which explanation correctly describes the decision mechanism?",
                    items=["The detailed explanation.", "An unrelated claim."],
                    answer_index=0,
                )
            )
        sections.append(
            CanvasSection(
                id=f"learning-{index}",
                title=f"Learning topic {index}",
                source_ref=f"Lecture.tex frames {index}",
                blocks=blocks,
            )
        )
    return CanvasDocument(
        id="generated-course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Generated lecture",
        source_kind="generated",
        source_ref="course planner from Lecture.tex",
        workspace_path="canvas/index.md",
        sections=sections,
    )

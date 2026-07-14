from __future__ import annotations

from pathlib import Path

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_prompt import planner_messages, repair_message, source_evidence
from lecturepilot.course_canvas_section_prompt import section_evidence
from lecturepilot.course_canvas_section_planner import (
    _section_messages,
    plan_sections_individually,
)
from lecturepilot.course_canvas_validation import (
    planned_section_bounds,
    source_topic_sections,
    validate_planned_document,
)
from lecturepilot.latex_canvas_importer import import_latex_canvas
from lecturepilot.models import ProviderSettings
from lecturepilot.providers import ProviderConfigurationError


def test_planner_uses_adaptive_section_targets_in_full_and_repair_contracts() -> None:
    short_source = _source_document(4)
    full_source = _source_document(10)

    assert planned_section_bounds(short_source) == (4, 7)
    assert planned_section_bounds(full_source) == (8, 12)
    assert "4 to 7 pedagogical sections" in planner_messages(short_source)[0]["content"]
    assert "8 to 12 pedagogical sections" in planner_messages(full_source)[0]["content"]
    assert "4 to 7 study sections" in repair_message("bad draft", short_source)["content"]
    assert "8 to 12 study sections" in repair_message("bad draft", full_source)["content"]


def test_full_lecture_validation_requires_eight_but_allows_twelve_sections() -> None:
    full_source = _source_document(10)

    validate_planned_document(_generated_document(12), full_source)
    with pytest.raises(ProviderConfigurationError, match="at least 8"):
        validate_planned_document(_generated_document(7), full_source)


def test_short_lecture_validation_does_not_force_eight_sections() -> None:
    validate_planned_document(_generated_document(4), _source_document(4))


def test_single_topic_lecture_uses_coherent_assessment_requirements() -> None:
    source = _source_document(1)

    validate_planned_document(_generated_document(1), source)
    prompt = planner_messages(source)[0]["content"]
    repair = repair_message("bad draft", source)["content"]
    assert "fewer than 3 sections" in prompt
    assert "at least one quiz" in prompt
    assert "fewer than 3 sections" in repair
    assert "at least one quiz" in repair


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
    assert planned_section_bounds(source) == (5, 7)


async def test_section_fallback_skips_asset_only_outline_sections() -> None:
    source = _source_document(7)
    source.sections.append(
        CanvasSection(
            id="original-slides",
            title="Original slides",
            source_ref="Lecture.pdf",
            blocks=[CanvasBlock(id="slide-1", type="asset", asset_path="slide-001.png")],
        )
    )
    client = _FallbackPlanClient()

    planned = await plan_sections_individually(
        model_client=client,
        settings=ProviderSettings(
            provider="test",
            model="test/model",
            api_key_env="TEST_API_KEY",
            capabilities=set(),
        ),
        source_document=source,
    )

    assert len(planned.sections) == 7
    assert "original-slides" not in client.source_ids


def test_planner_and_section_fallback_receive_materially_more_bounded_evidence() -> None:
    source = _source_document(60, text_size=2_000)
    full_evidence = source_evidence(source)
    fallback_evidence = section_evidence(source, _dense_section(text_size=4_000, block_count=8))

    assert 70_000 < len(full_evidence) <= 80_000
    assert 20_000 < len(fallback_evidence) <= 24_000
    assert (
        "4 to 8 detailed teaching blocks"
        in _section_messages(source, source.sections[0])[0]["content"]
    )


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
        if index == 1:
            blocks.append(
                CanvasBlock(id="opening-check", type="checkpoint", text="Explain the mechanism.")
            )
        if index == 2 or index == section_count:
            blocks.append(
                CanvasBlock(
                    id=f"quiz-{index}",
                    type="quiz",
                    text="Which explanation follows the source mechanism?",
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


class _FallbackPlanClient:
    def __init__(self) -> None:
        self.source_ids: list[str] = []

    async def complete_plan(self, *, settings, messages):
        evidence = messages[1]["content"]
        source_id = evidence.split("Required section id: ", 1)[1].splitlines()[0]
        self.source_ids.append(source_id)
        return {
            "sections": [
                {
                    "id": f"learning-{source_id}",
                    "title": f"Learning {source_id}",
                    "source_ref": f"Lecture.tex {source_id}",
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": "A source-grounded explanation of this learning topic.",
                        }
                    ],
                }
            ]
        }

from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_language import canvas_language_instruction
from lecturepilot.course_canvas_math import generated_math_instructions
from lecturepilot.course_canvas_validation import (
    planned_section_bounds,
    required_section_ids,
)


MAX_SOURCE_EVIDENCE_SECTIONS = 80
MAX_SOURCE_EVIDENCE_CHARS = 80_000
MAX_BLOCK_EVIDENCE_CHARS = 1_600


def planner_messages(
    source_document: CanvasDocument,
    *,
    output_language: str = "en",
) -> list[dict[str, str]]:
    min_sections, max_sections = planned_section_bounds(source_document)
    return [
        {
            "role": "system",
            "content": (
                "You are the LecturePilot course-builder agent. Create an editable, "
                "source-grounded study document from extracted lecture material. "
                f"{canvas_language_instruction(output_language)} "
                "Do not mirror slide-by-slide order, do not preserve extracted slide ids, "
                "and do not create one section per frame. Synthesize the full evidence into "
                f"{min_sections} to {max_sections} pedagogical sections with stable topic ids, four to eight detailed "
                "teaching blocks per section, key formulas, grouped lists, worked examples, "
                "callouts, infographic briefs, and existing source assets or videos when they help learning. "
                "Collapse long formula runs into a named derivation with only the essential equations. "
                f"{generated_math_instructions()} "
                "Make paragraphs self-study friendly: explain reason, mechanism, and consequence in "
                "2 to 4 sentences, then add examples or steps. Use light Markdown emphasis such as **posterior** or `p(x | C)`. "
                "When evidence contains relevant fenced code, preserve it inside a paragraph block "
                "with its language fence and indentation; never execute it. "
                "Leave room for professor-approved YouTube videos instead of inventing "
                "video links. When original slide image assets are listed, use one as "
                "the recognition anchor for each section and cite the matching PDF page or frame in source_ref. "
                "Return one structured draft with title and sections. Each section must "
                "include id, title, source_ref, and blocks. Blocks may be paragraph, list, "
                "callout, math, asset, video, table, checkpoint, or quiz. "
                f"{_assessment_instructions()} "
                "Every block must include id, type, text, items, asset_path, caption, and answer_index; use null or [] where not relevant. Quiz blocks use text as the question, items as answers, and answer_index for the correct option. Asset and video blocks may only use asset_path values "
                "listed in the evidence. Do not invent unsupported topics. Cite source "
                "files and frames in every source_ref. Never return a short overview."
            ),
        },
        {"role": "user", "content": source_evidence(source_document)},
    ]


def repair_message(
    error: str,
    source_document: CanvasDocument,
    *,
    output_language: str = "en",
) -> dict[str, str]:
    min_sections, max_sections = planned_section_bounds(source_document)
    return {
        "role": "user",
        "content": (
            f"The previous draft failed validation: {error}. Return a corrected JSON draft. "
            f"{canvas_language_instruction(output_language)} "
            f"Do not mirror extracted slide ids. Group source evidence into {min_sections} to {max_sections} study "
            "sections, cite source files and frames in source_ref, use 4 to 8 detailed "
            "teaching blocks and 600 explanatory characters per section. "
            f"{_assessment_instructions()} "
            "Source outline ids available for coverage: "
            f"{', '.join(required_section_ids(source_document)) or 'see evidence titles'}. "
            f"{generated_math_instructions()}"
        ),
    }


def _assessment_instructions() -> str:
    return (
        "For a draft with fewer than 3 sections, put a checkpoint or quiz in every section "
        "and include at least one quiz. Otherwise, spread assessment blocks across at least "
        "3 sections and include at least 2 quizzes. Place them after key concepts, worked "
        "examples, or skill transitions, with a final retrieval quiz in the last section."
    )


def source_evidence(document: CanvasDocument) -> str:
    sections = document.sections[:MAX_SOURCE_EVIDENCE_SECTIONS]
    lines = [
        f"Course id: {document.course_id}",
        f"Lecture id: {document.lecture_id}",
        f"Lecture title: {document.title}",
        f"Primary source: {document.source_ref}",
        "Extracted source outline; cover these topics but create new learning-section ids:",
    ]
    for index, section in enumerate(sections, start=1):
        lines.append(
            f"{index}. id={section.id}; title={section.title}; source_ref={section.source_ref}"
        )
    lines.append("\nExtracted source evidence by outline section:")
    prefix = "\n".join(lines)
    evidence_budget = max(MAX_SOURCE_EVIDENCE_CHARS - len(prefix) - 1, 0)
    evidence = _balanced_section_evidence(sections, evidence_budget)
    return _trim_layout(f"{prefix}\n{evidence}", MAX_SOURCE_EVIDENCE_CHARS)


def _balanced_section_evidence(sections: list[CanvasSection], limit: int) -> str:
    rendered = [
        "\n".join(
            [
                f"SECTION {section.id}: {section.title} ({section.source_ref or 'source unknown'})",
                *(_block_evidence(block) for block in section.blocks),
            ]
        )
        for section in sections
    ]
    separator_cost = max(len(rendered) - 1, 0) * 2
    allocations = _balanced_allocations(
        [len(value) for value in rendered], max(limit - separator_cost, 0)
    )
    return "\n\n".join(
        _trim_layout(value, allocation)
        for value, allocation in zip(rendered, allocations, strict=True)
    )


def _balanced_allocations(lengths: list[int], limit: int) -> list[int]:
    allocations = [0] * len(lengths)
    remaining = list(range(len(lengths)))
    while remaining:
        share = limit // len(remaining)
        completed = [index for index in remaining if lengths[index] <= share]
        if not completed:
            share, extra = divmod(limit, len(remaining))
            for position, index in enumerate(remaining):
                allocations[index] = share + (position < extra)
            break
        for index in completed:
            allocations[index] = lengths[index]
            limit -= lengths[index]
        remaining = [index for index in remaining if index not in completed]
    return allocations


def _block_evidence(block: CanvasBlock) -> str:
    if (
        block.type == "asset"
        and block.asset_path
        and block.asset_path.startswith("generated-slides/")
    ):
        return f"- original slide id={block.id}; asset_path={block.asset_path}; caption={block.caption or ''}"
    if block.type == "asset":
        return (
            f"- asset id={block.id}; asset_path={block.asset_path}; caption={block.caption or ''}"
        )
    if block.type == "video":
        return (
            f"- video id={block.id}; asset_path={block.asset_path}; caption={block.caption or ''}"
        )
    if block.type == "math":
        return f"- math id={block.id}: {_trim(block.text or '', MAX_BLOCK_EVIDENCE_CHARS)}"
    if block.type == "list":
        items = "; ".join(_trim(item, 180) for item in block.items[:18])
        return f"- list id={block.id}: {items}"
    if (block.text or "").lstrip().startswith(("```", "~~~")):
        return f"- code id={block.id}:\n{_trim_layout(block.text or '', 4000)}"
    return f"- {block.type} id={block.id}: {_trim(block.text or '', MAX_BLOCK_EVIDENCE_CHARS)}"


def _trim(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _trim_layout(value: str, limit: int) -> str:
    cleaned = value.strip()
    if len(cleaned) <= limit:
        return cleaned
    if limit <= 3:
        return cleaned[:limit]
    return cleaned[: limit - 3].rstrip() + "..."

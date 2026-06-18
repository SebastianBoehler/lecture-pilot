from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument
from lecturepilot.course_canvas_validation import required_section_ids


MAX_SOURCE_EVIDENCE_SECTIONS = 80


def planner_messages(source_document: CanvasDocument) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are the LecturePilot course-builder agent. Create an editable, "
                "source-grounded study document from extracted lecture material. "
                "Do not mirror slide-by-slide order, do not preserve extracted slide ids, "
                "and do not create one section per frame. Synthesize the full evidence into "
                "5 to 8 pedagogical sections with stable topic ids, four to seven detailed "
                "teaching blocks per section, key formulas, grouped lists, worked examples, "
                "callouts, infographic briefs, and existing source assets or videos when they help learning. "
                "Collapse long formula runs into a named derivation with only the essential equations. "
                "Make paragraphs self-study friendly: explain reason, mechanism, and consequence in "
                "2 to 4 sentences, then add examples or steps. Use light Markdown emphasis such as **posterior** or `p(x | C)`. "
                "Leave room for professor-approved YouTube videos instead of inventing "
                "video links. When original slide image assets are listed, use one as "
                "the recognition anchor for each section and cite the matching PDF page or frame in source_ref. "
                "Return one structured draft with title and sections. Each section must "
                "include id, title, source_ref, and blocks. Blocks may be paragraph, list, "
                "callout, math, asset, video, table, checkpoint, or quiz. Use "
                "3 to 5 checkpoint or quiz blocks across the lecture. Place them after key "
                "concepts, worked examples, or skill transitions; include at least two quiz "
                "blocks and a final retrieval quiz in the last section. "
                "Every block must include id, type, text, items, asset_path, caption, and answer_index; use null or [] where not relevant. Quiz blocks use text as the question, items as answers, and answer_index for the correct option. Asset and video blocks may only use asset_path values "
                "listed in the evidence. Do not invent unsupported topics. Cite source "
                "files and frames in every source_ref. Never return a short overview."
            ),
        },
        {"role": "user", "content": source_evidence(source_document)},
    ]


def repair_message(error: str, source_document: CanvasDocument) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            f"The previous draft failed validation: {error}. Return a corrected JSON draft. "
            "Do not mirror extracted slide ids. Group source evidence into 5 to 8 study "
            "sections, cite source files and frames in source_ref, use at least 4 "
            "teaching blocks and 600 explanatory characters per section, and spread checkpoint "
            "or quiz blocks across at least 3 sections with at least 2 quizzes. Source outline ids available for coverage: "
            f"{', '.join(required_section_ids(source_document)) or 'see evidence titles'}."
        ),
    }


def source_evidence(document: CanvasDocument) -> str:
    lines = [
        f"Course id: {document.course_id}",
        f"Lecture id: {document.lecture_id}",
        f"Lecture title: {document.title}",
        f"Primary source: {document.source_ref}",
        "Extracted source outline; cover these topics but create new learning-section ids:",
    ]
    for index, section in enumerate(document.sections[:MAX_SOURCE_EVIDENCE_SECTIONS], start=1):
        lines.append(f"{index}. id={section.id}; title={section.title}; source_ref={section.source_ref}")
    lines.append("\nExtracted source evidence by outline section:")
    for section in document.sections[:MAX_SOURCE_EVIDENCE_SECTIONS]:
        lines.append(f"\nSECTION {section.id}: {section.title} ({section.source_ref or 'source unknown'})")
        for block in section.blocks:
            lines.append(_block_evidence(block))
    return _trim("\n".join(lines), 50000)


def _block_evidence(block: CanvasBlock) -> str:
    if block.type == "asset" and block.asset_path and block.asset_path.startswith("generated-slides/"):
        return f"- original slide id={block.id}; asset_path={block.asset_path}; caption={block.caption or ''}"
    if block.type == "asset":
        return f"- asset id={block.id}; asset_path={block.asset_path}; caption={block.caption or ''}"
    if block.type == "video":
        return f"- video id={block.id}; asset_path={block.asset_path}; caption={block.caption or ''}"
    if block.type == "math":
        return f"- math id={block.id}: {_trim(block.text or '', 900)}"
    if block.type == "list":
        items = "; ".join(_trim(item, 180) for item in block.items[:18])
        return f"- list id={block.id}: {items}"
    return f"- {block.type} id={block.id}: {_trim(block.text or '', 900)}"


def _trim(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."

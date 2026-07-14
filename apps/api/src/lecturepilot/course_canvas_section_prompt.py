from __future__ import annotations

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.course_canvas_math import generated_math_instructions


MAX_SECTION_EVIDENCE_CHARS = 24_000


def section_messages(
    source_document: CanvasDocument, section: CanvasSection
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Rewrite this extracted lecture section into a clean markdown learning "
                "canvas section. Return one structured object with title and a sections array containing "
                "exactly one object with id, title, source_ref, and blocks. "
                "Use 4 to 8 detailed teaching blocks with self-study paragraphs, examples, and steps. "
                "Blocks may be paragraph, list, callout, math, asset, video, "
                "table, checkpoint, or quiz. Include a concise checkpoint or quiz when the "
                "section introduces a key concept, worked example, or procedure. Quiz blocks use text as the question and "
                "items as possible answers plus answer_index for the correct option. "
                "Every block must include id, type, text, items, asset_path, caption, "
                "and answer_index; use null or [] for fields that do not apply. "
                "Do not preserve raw slide ids; create a stable learning topic id. Preserve "
                "key formulas and source-backed assets. Add a worked example or infographic "
                "brief when it helps learning. Explain why each key idea matters before "
                "asking for retrieval. Use light Markdown for key terms and notation. "
                f"{generated_math_instructions()} "
                "Preserve relevant fenced code in paragraph text with its language and "
                "indentation; never execute it. Do not invent unsupported topics."
            ),
        },
        {"role": "user", "content": section_evidence(source_document, section)},
    ]


def section_evidence(source_document: CanvasDocument, section: CanvasSection) -> str:
    lines = [
        f"Course id: {source_document.course_id}",
        f"Lecture id: {source_document.lecture_id}",
        f"Primary source: {source_document.source_ref}",
        f"Required section id: {section.id}",
        f"Source section title: {section.title}",
        f"Source frames: {section.source_ref or 'unknown'}",
    ]
    for block in section.blocks:
        if block.type in {"asset", "video"}:
            lines.append(
                f"- {block.type} asset_path={block.asset_path}; caption={block.caption or ''}"
            )
        elif block.type == "list":
            lines.append("- list: " + "; ".join(block.items[:24]))
        else:
            lines.append(f"- {block.type}: {block.text or ''}")
    return _trim_layout("\n".join(lines), MAX_SECTION_EVIDENCE_CHARS)


def _trim_layout(value: str, limit: int) -> str:
    cleaned = value.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."

from __future__ import annotations

from lecturepilot.assessment_prompts import assessment_generation_instruction
from lecturepilot.canvas_component_catalog import component_catalog_instruction
from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.course_canvas_language import canvas_language_instruction
from lecturepilot.course_canvas_math import generated_math_instructions


MAX_SECTION_EVIDENCE_CHARS = 24_000


def section_messages(
    source_document: CanvasDocument,
    section: CanvasSection,
    *,
    output_language: str = "en",
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Rewrite this extracted lecture section into a clean markdown learning "
                "canvas section. Return one structured object with title and a sections array containing "
                f"{canvas_language_instruction(output_language)} "
                "exactly one object with title and blocks. The server derives section ids, block "
                "ids, and source provenance from the supplied evidence. "
                "Let the section's depth and structure follow the supplied evidence. Explain "
                "all material needed for independent study with source-backed paragraphs, "
                "examples, or steps; do not pad thin evidence or omit dense evidence to meet "
                "a length or block-count quota. "
                "Blocks may be paragraph, list, callout, math, asset, video, "
                "table, checkpoint, quiz, or component. "
                f"{component_catalog_instruction()} "
                "Every generated teaching section must contain at least one concise, "
                "source-grounded open-response checkpoint. A quiz may be added as a second "
                "assessment, but it does not replace the checkpoint. Quiz blocks "
                "must have exactly one source-supported correct option and plausible distractors. "
                "Every assessment text must be a specific, standalone question or concrete task "
                "that is understandable without the surrounding section. Put labels such as "
                "'Checkpoint' or 'Why this matters' in caption only. Do not refer to an exercise "
                "sheet, slide, source, section, or earlier question without restating its context. "
                "Do not use generic 'explain the key mechanism' or 'as you would in an exam "
                "answer' phrasing. Quiz text must be one direct question ending in a question mark. "
                f"{assessment_generation_instruction()} "
                "Use text as the question, items as possible answers, and the zero-based "
                "answer_index of the correct option. Never guess an answer key. "
                "Return only the fields required by each block type; do not emit null placeholders. "
                "Do not preserve raw slide ids; create a stable learning topic id. Preserve "
                "key formulas and source-backed assets. Add a worked example or infographic "
                "brief when it helps learning. Explain why each key idea matters before "
                "asking for retrieval. Use light Markdown for key terms and notation. "
                f"{generated_math_instructions()} "
                "Preserve relevant fenced code in paragraph text with its language and "
                "indentation; never execute it. Never collapse source code into one line. "
                "Put fences on their own lines, preserve source line breaks, and indent nested "
                "blocks. If extraction provides one-line C/Java-style code, restore structural "
                "line breaks after braces and statements. Every teaching claim and selected quiz "
                "answer must follow from the supplied professor evidence. Do not invent "
                "unsupported topics."
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

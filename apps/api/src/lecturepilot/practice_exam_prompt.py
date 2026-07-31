from __future__ import annotations

from lecturepilot.canvas_models import CanvasDocument


MAX_COURSE_EVIDENCE_CHARS = 60_000
MAX_PPI_EVIDENCE_CHARS = 30_000
MAX_COURSE_EVIDENCE_ITEM_CHARS = 2_400


def practice_exam_messages(
    *,
    course_title: str,
    language: str,
    duration_minutes: int,
    question_count: int,
    course_evidence: str,
    ppi_evidence: str,
    repair_error: str | None = None,
) -> list[dict[str, str]]:
    repair = f" Repair the prior attempt because: {repair_error}" if repair_error else ""
    system = (
        "Create one rigorous university practice exam as strict structured JSON. "
        f"Write exactly {question_count} questions in language {language} for a "
        f"{duration_minutes}-minute exam. Mix multiple-choice and open-ended questions, "
        "vary difficulty, assign sensible points, and include private answer keys or rubrics. "
        "Every question must cite at least one supplied authoritative course source id. "
        "Cover every lecture represented in the evidence before repeating a lecture, then maximize "
        "section and concept breadth before adding variants of an already tested concept. "
        "PPI material is non-authoritative pattern evidence only: use it to infer style, topic "
        "weight, and format, never as the sole factual source and never copy its wording. "
        "Create original standalone questions. Multiple-choice questions need distinct plausible "
        "options and one valid zero-based answer_index; their rubric must be empty. Open-ended "
        "questions need an empty options list, null answer_index, concrete rubric criteria, and "
        "a concise reference_answer that would earn full points. Multiple-choice questions need "
        "a null reference_answer. "
        "Use stable ids q-01, q-02, and so on. Cite selected PPI ids only when their pattern "
        "materially influenced a question. Instructions must contain only learner actions: never "
        "repeat the duration, question count, total points, or answer-index conventions. "
        "In instructions, prompts, options, and rubrics, use only light Markdown: **bold**, "
        "*emphasis*, backticks for literal code or tokens, $...$ for inline math, and $$...$$ "
        "for display math. Do not emit raw HTML, headings, links, tables, fenced code blocks, "
        "or LaTeX document commands. "
        f"{repair}"
    )
    user = (
        f"Course: {course_title}\n\n"
        "Authoritative unlocked course evidence:\n"
        f"{_trim(course_evidence, MAX_COURSE_EVIDENCE_CHARS)}\n\n"
        "Optional non-authoritative pattern evidence from private PPI imports:\n"
        f"{_trim(ppi_evidence, MAX_PPI_EVIDENCE_CHARS) if ppi_evidence else '(none)'}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def authoritative_canvas_evidence(documents: list[CanvasDocument]) -> tuple[str, set[str]]:
    lines: list[str] = []
    source_ids: set[str] = set()
    used_characters = 0
    document_items = [_document_evidence_items(document) for document in documents]
    for document in documents:
        header = f"Lecture: {document.title} ({document.lecture_id})"
        used_characters, added = _append_bounded(lines, header, used_characters)
        if not added:
            return "\n".join(lines), source_ids
    positions = [0] * len(document_items)
    while True:
        found_item = False
        for index, items in enumerate(document_items):
            if positions[index] >= len(items):
                continue
            found_item = True
            source_id, line = items[positions[index]]
            positions[index] += 1
            remaining = MAX_COURSE_EVIDENCE_CHARS - used_characters - (1 if lines else 0)
            if remaining < 80:
                return "\n".join(lines), source_ids
            bounded = _trim(line, min(MAX_COURSE_EVIDENCE_ITEM_CHARS, remaining))
            used_characters, added = _append_bounded(lines, bounded, used_characters)
            if added:
                source_ids.add(source_id)
        if not found_item:
            break
    return "\n".join(lines), source_ids


def _document_evidence_items(document: CanvasDocument) -> list[tuple[str, str]]:
    section_items: list[list[tuple[str, str]]] = []
    for section in document.sections:
        items: list[tuple[str, str]] = []
        for block in section.blocks:
            content = block.text or "\n".join(block.items)
            if not content.strip() or block.type in {"asset", "video"}:
                continue
            source_id = f"{document.lecture_id}:{section.id}:{block.id}"
            items.append((source_id, f"[{source_id}] {section.title}: {content.strip()}"))
        section_items.append(items)
    interleaved: list[tuple[str, str]] = []
    for position in range(max((len(items) for items in section_items), default=0)):
        interleaved.extend(items[position] for items in section_items if position < len(items))
    return interleaved


def ppi_pattern_evidence(sources: dict[str, list[str]]) -> str:
    lines = []
    for source_id in sorted(sources):
        lines.append(f"PPI pattern source [{source_id}]")
        lines.extend(text.strip() for text in sources[source_id] if text.strip())
    return "\n".join(lines)


def _trim(value: str, limit: int) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."


def _append_bounded(lines: list[str], line: str, used: int) -> tuple[int, bool]:
    required = len(line) + (1 if lines else 0)
    if used + required > MAX_COURSE_EVIDENCE_CHARS:
        return used, False
    lines.append(line)
    return used + required, True

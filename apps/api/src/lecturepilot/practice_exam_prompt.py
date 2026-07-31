from __future__ import annotations

from lecturepilot.canvas_models import CanvasDocument


MAX_COURSE_EVIDENCE_CHARS = 60_000
MAX_PPI_EVIDENCE_CHARS = 30_000


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
        "PPI material is non-authoritative pattern evidence only: use it to infer style, topic "
        "weight, and format, never as the sole factual source and never copy its wording. "
        "Create original standalone questions. Multiple-choice questions need distinct plausible "
        "options and one valid zero-based answer_index; their rubric must be empty. Open-ended "
        "questions need an empty options list, null answer_index, and concrete rubric criteria. "
        "Use stable ids q-01, q-02, and so on. Cite selected PPI ids only when their pattern "
        f"materially influenced a question.{repair}"
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
    for document in documents:
        header = f"Lecture: {document.title} ({document.lecture_id})"
        used_characters, added = _append_bounded(lines, header, used_characters)
        if not added:
            break
        for section in document.sections:
            for block in section.blocks:
                content = block.text or "\n".join(block.items)
                if not content.strip() or block.type in {"asset", "video"}:
                    continue
                source_id = f"{document.lecture_id}:{section.id}:{block.id}"
                line = f"[{source_id}] {section.title}: {content.strip()}"
                used_characters, added = _append_bounded(lines, line, used_characters)
                if added:
                    source_ids.add(source_id)
    return "\n".join(lines), source_ids


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

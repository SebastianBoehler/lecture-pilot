from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection


MAX_QUALITY_PROMPT_CHARS = 19_500


def compact_quality_evidence(
    source_document: CanvasDocument,
    candidate_document: CanvasDocument,
) -> str:
    """Build a bounded claim-to-evidence ledger for the semantic critic."""
    sections = candidate_document.sections
    if not sections:
        return "No candidate sections."
    complete = "\n\n".join(
        _complete_section_unit(section, source_document.sections) for section in sections
    )
    if len(complete) <= MAX_QUALITY_PROMPT_CHARS:
        return complete
    budget = max(1_000, MAX_QUALITY_PROMPT_CHARS // len(sections))
    units = [_section_unit(section, source_document.sections, budget) for section in sections]
    return "\n\n".join(units)[:MAX_QUALITY_PROMPT_CHARS]


def quality_review_batches(
    source_document: CanvasDocument,
    candidate_document: CanvasDocument,
) -> list[list[CanvasSection]]:
    batches: list[list[CanvasSection]] = []
    active: list[CanvasSection] = []
    used = 0
    for section in candidate_document.sections:
        size = len(_complete_section_unit(section, source_document.sections))
        if active and used + size + 2 > MAX_QUALITY_PROMPT_CHARS:
            batches.append(active)
            active = []
            used = 0
        active.append(section)
        used += size + (2 if used else 0)
    if active:
        batches.append(active)
    return batches


def _complete_section_unit(
    candidate: CanvasSection,
    source_sections: list[CanvasSection],
) -> str:
    return _section_unit(candidate, source_sections, MAX_QUALITY_PROMPT_CHARS * 100)


def _section_unit(
    candidate: CanvasSection,
    source_sections: list[CanvasSection],
    budget: int,
) -> str:
    header = [
        f"CANDIDATE SECTION {candidate.id}",
        f"Title: {candidate.title}",
        f"Evidence refs: {candidate.source_ref or 'unknown'}",
    ]
    candidate_lines = [line for block in candidate.blocks if (line := _candidate_line(block))]
    matched = _matching_sources(candidate, source_sections)
    source_lines: list[str] = []
    for source in matched:
        source_lines.append(f"SOURCE EVIDENCE {source.source_ref or source.title}")
        source_lines.extend(line for block in source.blocks if (line := _source_line(block)))
    candidate_budget = max(500, budget // 2)
    first = _bounded_lines([*header, *candidate_lines], candidate_budget)
    remaining = max(0, budget - len(first) - 1)
    evidence = _bounded_lines(source_lines, remaining)
    return f"{first}\n{evidence}".rstrip()


def _matching_sources(
    candidate: CanvasSection,
    source_sections: list[CanvasSection],
) -> list[CanvasSection]:
    refs = candidate.source_ref or ""
    matched = [
        section for section in source_sections if section.source_ref and section.source_ref in refs
    ]
    return matched or source_sections[:1]


def _candidate_line(block: CanvasBlock) -> str:
    prefix = f"CANDIDATE BLOCK {block.id} [{block.type}]"
    if block.type in {"list", "quiz"} or block.items:
        answer = f"; selected={block.answer_index}" if block.answer_index is not None else ""
        return f"{prefix}: {block.text or ''}; options={block.items}{answer}"
    if block.type in {"asset", "video"}:
        return f"{prefix}: {block.asset_path}; {block.caption or ''}"
    return f"{prefix}: {block.text or block.caption or ''}"


def _source_line(block: CanvasBlock) -> str:
    if block.type == "list":
        return f"- list: {'; '.join(block.items)}"
    if block.type in {"asset", "video"}:
        return f"- {block.type}: {block.asset_path}; {block.caption or ''}"
    return f"- {block.type}: {block.text or block.caption or ''}"


def _bounded_lines(lines: list[str], budget: int) -> str:
    output: list[str] = []
    used = 0
    for line in lines:
        normalized = " ".join(line.split())
        remaining = budget - used
        if remaining <= 0:
            break
        if len(normalized) > remaining:
            continue
        output.append(normalized)
        used += len(normalized) + 1
    return "\n".join(output)

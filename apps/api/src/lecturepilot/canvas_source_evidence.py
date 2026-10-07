from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection

MAX_SOURCE_EVIDENCE_SECTIONS = 80
MAX_SOURCE_EVIDENCE_CHARS = 80_000
MAX_BLOCK_EVIDENCE_CHARS = 1_600


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

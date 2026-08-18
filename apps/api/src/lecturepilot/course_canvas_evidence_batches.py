from __future__ import annotations

from lecturepilot.canvas_models import CanvasSection


MAX_LEARNING_SECTIONS = 5
MAX_SECTION_SOURCE_REF_CHARS = 500


def group_evidence_sections(
    sections: list[CanvasSection],
    *,
    max_groups: int = MAX_LEARNING_SECTIONS,
    document_source_ref: str | None = None,
) -> list[CanvasSection]:
    """Combine adjacent source frames into a bounded learning-section outline."""
    sections = [_qualified_ref(section, document_source_ref) for section in sections]
    if len(sections) <= max_groups:
        return sections
    group_count = min(len(sections), max_groups)
    base_size, larger_groups = divmod(len(sections), group_count)
    groups: list[CanvasSection] = []
    cursor = 0
    for index in range(group_count):
        size = base_size + (1 if index < larger_groups else 0)
        source_group = sections[cursor : cursor + size]
        cursor += size
        groups.append(_merge_group(index + 1, source_group))
    return groups


def _qualified_ref(section: CanvasSection, document_source_ref: str | None) -> CanvasSection:
    section_ref = section.source_ref or ""
    if not document_source_ref or document_source_ref.casefold() in section_ref.casefold():
        return section
    return section.model_copy(update={"source_ref": f"{document_source_ref} {section_ref}".strip()})


def _merge_group(index: int, sections: list[CanvasSection]) -> CanvasSection:
    refs = list(dict.fromkeys(section.source_ref for section in sections if section.source_ref))
    first_title = sections[0].title
    last_title = sections[-1].title
    title = first_title if first_title == last_title else f"{first_title} to {last_title}"
    return CanvasSection(
        id=f"evidence-batch-{index}",
        title=title[:200],
        source_ref=" | ".join(refs)[:MAX_SECTION_SOURCE_REF_CHARS],
        blocks=[block for section in sections for block in section.blocks],
    )

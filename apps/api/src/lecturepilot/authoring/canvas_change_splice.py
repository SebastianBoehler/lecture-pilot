"""Splice regenerated sections into an unchanged base lecture and check the whole lecture.

Every section that is not regenerated is taken from the base document object itself, so it
stays byte-identical when the draft is stored. Regenerated sections follow the lecture-wide
rules of ordinary authoring: one prediction card per lecture, colliding block ids renamed,
original slides interleaved, then the same deterministic lecture checks.
"""

from lecturepilot.authoring.course_canvas_practice_contract import validate_practice_candidate
from lecturepilot.authoring.course_canvas_validation import validate_planned_document
from lecturepilot.canvas.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.canvas.quiz_identity import validate_unique_quiz_ids
from lecturepilot.core.storage_layout import safe_id
from lecturepilot.learning_design.learning_map import validate_learning_contract_ids
from lecturepilot.sources.course_slide_interleaving import interleave_original_slides


def splice_sections(
    base: CanvasDocument, changed: dict[str, CanvasSection], source: CanvasDocument
) -> CanvasDocument:
    """`changed` maps base section ids to their regenerated sections."""
    kept = [section for section in base.sections if section.id not in changed]
    seen = {block.id for section in kept for block in section.blocks}
    prediction = any(block.type == "prediction" for s in kept for block in s.blocks)
    sections = []
    for section in base.sections:
        if section.id not in changed:
            sections.append(section)
            continue
        blocks = []
        prefix = safe_id(section.source_section_id or section.id)[:48]
        for block in changed[section.id].blocks:
            if block.type == "prediction":
                if prediction or not (block.text or "").strip():
                    continue
                prediction = True
            if block.id in seen and not block.id.startswith("practice-"):
                block = block.model_copy(update={"id": f"{prefix}-{block.id}"[:120]})
            seen.add(block.id)
            blocks.append(block)
        sections.append(changed[section.id].model_copy(update={"blocks": blocks}))
    document = base.model_copy(update={"sections": sections})
    interleaved = {s.id: s for s in interleave_original_slides(document, source).sections}
    return base.model_copy(
        update={
            "sections": [
                interleaved.get(section.id, section) if section.id in changed else section
                for section in base.sections
            ]
        }
    )


def restore_unchanged(
    base: CanvasDocument, document: CanvasDocument, changed_ids
) -> CanvasDocument:
    """After media placement, keep base sections exactly and add no new sections."""
    by_id = {section.id: section for section in document.sections}
    return document.model_copy(
        update={
            "sections": [
                by_id.get(section.id, section) if section.id in changed_ids else section
                for section in base.sections
            ]
        }
    )


def validate_lecture(document: CanvasDocument, source: CanvasDocument, design) -> None:
    validate_planned_document(document, source)
    validate_practice_candidate(document, design, source_document=source)
    validate_unique_quiz_ids(document)
    validate_learning_contract_ids(document)

from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection


def enrich_learning_document(document: CanvasDocument) -> CanvasDocument:
    total = len(document.sections)
    sections = [
        _enrich_section(section, index, total)
        for index, section in enumerate(document.sections, start=1)
    ]
    return document.model_copy(update={"sections": sections})


def _enrich_section(section: CanvasSection, index: int, total: int) -> CanvasSection:
    wants_checkpoint = index == max(1, total // 2)
    wants_quiz = index == total
    blocks = _teaching_blocks(section.blocks)
    ids = {block.id for block in blocks}
    if wants_checkpoint and not any(block.type == "checkpoint" for block in blocks):
        block_id = _unique_id(f"{section.id}-checkpoint", ids)
        blocks.append(
            CanvasBlock(
                id=block_id,
                type="checkpoint",
                caption="Quality gate",
                text=(
                    f"Explain the key mechanism in **{section.title}** in your own words, "
                    "then name one decision consequence or failure mode."
                ),
            )
        )
    if wants_quiz and not any(block.type == "quiz" for block in blocks):
        block_id = _unique_id(f"{section.id}-quiz", ids)
        blocks.append(
            CanvasBlock(
                id=block_id,
                type="quiz",
                caption="Retrieval check",
                text=f"Which answer best captures **{section.title}**?",
                items=_quiz_items(section.title),
                answer_index=0,
            )
        )
    return section.model_copy(update={"blocks": blocks})


def _quiz_items(title: str) -> list[str]:
    return [
        f"The concept controls how we reason about {title.lower()}.",
        "It is only a notation detail and does not change decisions.",
        "It can be ignored once a model has produced any probability.",
    ]


def _teaching_blocks(blocks: list[CanvasBlock]) -> list[CanvasBlock]:
    return [block for block in blocks if block.type not in {"checkpoint", "quiz"}]


def _unique_id(base: str, existing: set[str]) -> str:
    if base not in existing:
        existing.add(base)
        return base
    suffix = 2
    while f"{base}-{suffix}" in existing:
        suffix += 1
    value = f"{base}-{suffix}"
    existing.add(value)
    return value

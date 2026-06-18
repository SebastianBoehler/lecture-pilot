from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection


MIN_TEACHING_BLOCKS = 4
MIN_DETAIL_CHARS = 600


def enrich_learning_document(document: CanvasDocument) -> CanvasDocument:
    total = len(document.sections)
    sections = [
        _enrich_section(section, index, total)
        for index, section in enumerate(document.sections, start=1)
    ]
    return document.model_copy(update={"sections": sections})


def _enrich_section(section: CanvasSection, index: int, total: int) -> CanvasSection:
    wants_checkpoint, wants_quiz = _assessment_targets(index, total)
    blocks = _complete_teaching_blocks(section)
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


def _assessment_targets(index: int, total: int) -> tuple[bool, bool]:
    checkpoint_index = max(1, min(total, (total + 1) // 3))
    practice_quiz_index = max(checkpoint_index + 1, min(total, (2 * total + 2) // 3))
    wants_checkpoint = index == checkpoint_index
    wants_quiz = index in {practice_quiz_index, total}
    return wants_checkpoint, wants_quiz


def _complete_teaching_blocks(section: CanvasSection) -> list[CanvasBlock]:
    blocks = list(section.blocks)
    ids = {block.id for block in blocks}
    while len(_teaching_blocks(blocks)) < MIN_TEACHING_BLOCKS:
        block = _support_block(section, len(blocks) + 1, ids)
        blocks.append(block)
        ids.add(block.id)
    if _detail_chars(_teaching_blocks(blocks)) < MIN_DETAIL_CHARS:
        blocks.append(_support_block(section, len(blocks) + 1, ids))
    return blocks


def _support_block(section: CanvasSection, index: int, ids: set[str]) -> CanvasBlock:
    block_id = _unique_id(f"{section.id}-study-support-{index}", ids)
    anchor = _section_anchor(section)
    if index % 3 == 1:
        return CanvasBlock(
            id=block_id,
            type="paragraph",
            text=(
                f"**Why this matters.** {section.title} turns the source material into a decision step. "
                f"The key cue is {anchor}. Use it to identify the quantity being estimated, state what "
                "evidence changes it, and connect the result to the decision the learner must make."
            ),
        )
    if index % 3 == 2:
        return CanvasBlock(
            id=block_id,
            type="list",
            items=[
                "Name the source variable or formula before interpreting it.",
                "Explain which part comes from evidence and which part is a modeling choice.",
                "Check how the conclusion would change under a different cost or observation.",
            ],
        )
    return CanvasBlock(
        id=block_id,
        type="callout",
        text=(
            f"Learning checkpoint: use {anchor} to rephrase the section without slide wording. "
            "A good answer should include the mechanism, a concrete example, and one limitation or "
            "failure mode."
        ),
    )


def _section_anchor(section: CanvasSection) -> str:
    parts: list[str] = []
    for block in section.blocks:
        parts.extend((block.text or block.caption or "").replace("`", "").split())
        parts.extend(" ".join(block.items).split())
        if len(parts) >= 12:
            break
    return " ".join(parts[:12]) or "the visible formulas, media, and notes"


def _detail_chars(blocks: list[CanvasBlock]) -> int:
    return sum(len(block.text or "") + sum(len(item) for item in block.items) for block in blocks)


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

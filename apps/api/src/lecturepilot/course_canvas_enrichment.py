from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_learning_support import (
    support_check_prompt,
    support_study_items,
    support_why_text,
)


MIN_TEACHING_BLOCKS = 4
MIN_DETAIL_CHARS = 600


def enrich_learning_document(
    document: CanvasDocument, *, output_language: str = "en"
) -> CanvasDocument:
    total = len(document.sections)
    sections = [
        _enrich_section(section, index, total, output_language)
        for index, section in enumerate(document.sections, start=1)
    ]
    return document.model_copy(update={"sections": sections})


def _enrich_section(
    section: CanvasSection, index: int, total: int, output_language: str
) -> CanvasSection:
    wants_checkpoint, wants_quiz = _assessment_targets(index, total)
    blocks = _complete_teaching_blocks(section, output_language)
    ids = {block.id for block in blocks}
    if wants_checkpoint and not any(block.type == "checkpoint" for block in blocks):
        block_id = _unique_id(f"{section.id}-checkpoint", ids)
        blocks.append(
            CanvasBlock(
                id=block_id,
                type="checkpoint",
                caption=("Lernzielkontrolle" if output_language == "de" else "Quality gate"),
                text=_checkpoint_text(section.title, output_language),
            )
        )
    if wants_quiz and not any(block.type == "quiz" for block in blocks):
        block_id = _unique_id(f"{section.id}-quiz", ids)
        blocks.append(
            CanvasBlock(
                id=block_id,
                type="quiz",
                caption=("Abrufübung" if output_language == "de" else "Retrieval check"),
                text=_quiz_text(section.title, output_language),
                items=_quiz_items(section.title, output_language),
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


def _complete_teaching_blocks(section: CanvasSection, output_language: str) -> list[CanvasBlock]:
    blocks = list(section.blocks)
    ids = {block.id for block in blocks}
    while len(_teaching_blocks(blocks)) < MIN_TEACHING_BLOCKS:
        block = _support_block(section, len(blocks) + 1, ids, output_language)
        blocks.append(block)
        ids.add(block.id)
    if _detail_chars(_teaching_blocks(blocks)) < MIN_DETAIL_CHARS:
        blocks.append(_support_block(section, len(blocks) + 1, ids, output_language))
    return blocks


def _support_block(
    section: CanvasSection, index: int, ids: set[str], output_language: str
) -> CanvasBlock:
    block_id = _unique_id(f"{section.id}-study-support-{index}", ids)
    anchor = _section_anchor(section)
    if index % 3 == 1:
        return CanvasBlock(
            id=block_id,
            type="paragraph",
            text=support_why_text(section.title, anchor, output_language),
        )
    if index % 3 == 2:
        return CanvasBlock(
            id=block_id,
            type="list",
            items=support_study_items(output_language),
        )
    return CanvasBlock(
        id=block_id,
        type="callout",
        text=support_check_prompt(section.title, output_language),
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


def _checkpoint_text(title: str, output_language: str) -> str:
    if output_language == "de":
        return (
            f"Erkläre den zentralen Mechanismus von **{title}** in eigenen Worten und nenne "
            "anschließend eine Konsequenz für Entscheidungen oder einen möglichen Fehlerfall."
        )
    return (
        f"Explain the key mechanism in **{title}** in your own words, "
        "then name one decision consequence or failure mode."
    )


def _quiz_text(title: str, output_language: str) -> str:
    if output_language == "de":
        return f"Welche Antwort beschreibt **{title}** am besten?"
    return f"Which answer best captures **{title}**?"


def _quiz_items(title: str, output_language: str) -> list[str]:
    if output_language == "de":
        return [
            f"Das Konzept bestimmt, wie wir über {title.lower()} argumentieren.",
            "Es ist nur ein Detail der Notation und verändert keine Entscheidungen.",
            "Es kann ignoriert werden, sobald ein Modell irgendeine Wahrscheinlichkeit ausgegeben hat.",
        ]
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

from __future__ import annotations

import re

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection


_LEGACY_CHECKPOINT_RE = re.compile(
    r"^Learning checkpoint: use .+? to rephrase the section without slide wording\. "
    r"A good answer should include the mechanism, a concrete example, and one limitation or "
    r"failure mode\.$",
    re.DOTALL,
)
_LEGACY_WHY_RE = re.compile(
    r"^\*\*Why this matters\.\*\* .+? turns the source material into a decision step\. "
    r"The key cue is (?P<anchor>.+?)\. Use it to identify the quantity being estimated, "
    r"state what evidence changes it, and connect the result to the decision the learner must make\.$",
    re.DOTALL,
)
_LEGACY_STUDY_ITEMS = [
    "Name the source variable or formula before interpreting it.",
    "Explain which part comes from evidence and which part is a modeling choice.",
    "Check how the conclusion would change under a different cost or observation.",
]


def support_check_prompt(section_title: str) -> str:
    return (
        f"Check yourself: In **{section_title}**, what would you compute or compare first, and why? "
        "Answer with one concrete example from this section and one limitation or failure mode."
    )


def support_why_text(section_title: str, anchor: str) -> str:
    return (
        f"**Why this matters.** {section_title} is useful when the concept changes a decision, "
        f"estimate, or model comparison. Focus on {anchor}. Ask what quantity or case is being "
        "estimated, what evidence changes it, and what action would change if the answer changed."
    )


def support_study_items() -> list[str]:
    return [
        "Identify the relevant variable, formula, metric, or case before interpreting it.",
        "Separate what is observed in the data from what is chosen by the modeler.",
        "Describe how the conclusion would change under a different threshold, cost, or observation.",
    ]


def normalize_learning_support(document: CanvasDocument) -> CanvasDocument:
    sections = [_normalize_section(section) for section in document.sections]
    return document.model_copy(update={"sections": sections})


def _normalize_section(section: CanvasSection) -> CanvasSection:
    blocks = [_normalize_block(block, section.title) for block in section.blocks]
    return section.model_copy(update={"blocks": blocks})


def _normalize_block(block: CanvasBlock, section_title: str) -> CanvasBlock:
    if block.type == "list" and block.items == _LEGACY_STUDY_ITEMS:
        return block.model_copy(update={"items": support_study_items()})
    if not block.text:
        return block
    if block.type == "paragraph":
        match = _LEGACY_WHY_RE.match(block.text.strip())
        if match:
            return block.model_copy(
                update={"text": support_why_text(section_title, match.group("anchor"))}
            )
    if block.type != "callout" or not _LEGACY_CHECKPOINT_RE.match(block.text.strip()):
        return block
    return block.model_copy(update={"text": support_check_prompt(section_title)})

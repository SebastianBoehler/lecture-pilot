from __future__ import annotations

import re

from lecturepilot.assessment_prompts import assessment_prompt_issue
from lecturepilot.canvas_models import CanvasBlock, CanvasSection


_LABEL = re.compile(r"^[^:]{1,40}:\s*")
_INSTRUCTIONAL_TYPES = {"paragraph", "callout", "list", "table"}


def normalize_section_assessments(
    section: CanvasSection,
    *,
    output_language: str,
    require_checkpoint: bool = True,
) -> CanvasSection:
    blocks = list(section.blocks)
    evidence = _instructional_statement(blocks)
    checkpoint_found = False
    for index, block in enumerate(blocks):
        if block.type != "checkpoint":
            continue
        checkpoint_found = True
        issue = assessment_prompt_issue(block.text, "checkpoint")
        if not issue:
            continue
        statement = evidence if "not stated" in issue else _usable_statement(block.text) or evidence
        if statement:
            blocks[index] = block.model_copy(
                update={"text": _explanation_task(statement, output_language)}
            )
    if require_checkpoint and not checkpoint_found and evidence:
        blocks.append(
            CanvasBlock(
                id=_unique_checkpoint_id(section),
                type="checkpoint",
                caption="Checkpoint",
                text=_explanation_task(evidence, output_language),
            )
        )
    return section.model_copy(update={"blocks": blocks})


def _instructional_statement(blocks: list[CanvasBlock]) -> str | None:
    for block in blocks:
        if block.type not in _INSTRUCTIONAL_TYPES:
            continue
        value = block.text or (block.items[0] if block.items else "")
        if statement := _usable_statement(value):
            return statement
    return None


def _usable_statement(value: str | None) -> str | None:
    statement = " ".join((value or "").split())
    statement = _LABEL.sub("", statement).strip()
    statement = re.sub(r"\bthe source evidence\b", "the stated evidence", statement, flags=re.I)
    statement = re.sub(r"\bthe source\b", "the stated material", statement, flags=re.I)
    statement = re.sub(r"\bthis section\b", "this statement", statement, flags=re.I)
    if len(statement) < 20:
        return None
    return statement[:900]


def _explanation_task(statement: str, output_language: str) -> str:
    if output_language.casefold().startswith("de"):
        prefix = "Erkläre diese Aussage und benenne den beschriebenen Zusammenhang: "
    else:
        prefix = "Explain this statement and identify the relationship it describes: "
    return f"{prefix}{statement}"


def _unique_checkpoint_id(section: CanvasSection) -> str:
    reserved = {block.id for block in section.blocks}
    base = f"{section.id}-checkpoint-auto"
    candidate = base[:120]
    suffix = 2
    while candidate in reserved:
        tail = f"-{suffix}"
        candidate = f"{base[: 120 - len(tail)]}{tail}"
        suffix += 1
    return candidate

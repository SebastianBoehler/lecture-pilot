from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.model_generated_ids import safe_generated_id, student_section_id, trim_generated_text
from lecturepilot.models import AgentTurnInput, CanvasCommand

_GENERATED_BLOCK_TYPES = {
    "paragraph",
    "list",
    "callout",
    "math",
    "table",
    "checkpoint",
    "quiz",
    "component",
}


def read_generated_section(raw_command: dict) -> CanvasSection | None:
    raw_section = raw_command.get("section")
    if not isinstance(raw_section, dict):
        return None
    title = str(raw_section.get("title") or "Generated learning note").strip()[:200]
    raw_id = str(raw_section.get("id") or raw_command.get("section_id") or title)
    section_id = student_section_id(raw_id)
    blocks = _read_generated_blocks(raw_section.get("blocks"), section_id)
    if not blocks:
        return None
    return CanvasSection(id=section_id, title=title, source_ref="student workspace", blocks=blocks[:8])


def ensure_requested_learning_blocks(command: CanvasCommand, turn: AgentTurnInput) -> CanvasCommand:
    if command.type not in {"append_section", "update_section"} or command.section is None:
        return command
    requested = _requested_blocks(turn.message)
    if not any(requested.values()):
        return command
    blocks = list(command.section.blocks)
    present = {block.type for block in blocks}
    if requested["table"] and "table" not in present:
        blocks.append(_fallback_table(command.section.id))
    if requested["component"] and "component" not in present:
        blocks.append(_fallback_component(command.section.id))
    if requested["checkpoint"] and "checkpoint" not in present:
        blocks.append(_fallback_checkpoint(command.section.id))
    if requested["quiz"] and "quiz" not in present:
        blocks.append(_fallback_quiz(command.section.id))
    section = command.section.model_copy(update={"blocks": blocks[:8]})
    return command.model_copy(update={"section": section})


def _requested_blocks(message: str) -> dict[str, bool]:
    lowered = message.lower()
    return {
        "checkpoint": "checkpoint" in lowered or "gate" in lowered,
        "component": "component" in lowered or "interactive" in lowered,
        "quiz": "quiz" in lowered,
        "table": "table" in lowered,
    }


def _read_generated_blocks(raw_blocks: object, section_id: str) -> list[CanvasBlock]:
    if not isinstance(raw_blocks, list):
        return []
    return [
        _read_generated_block(raw_block, section_id, index)
        for index, raw_block in enumerate(raw_blocks[:10], start=1)
        if isinstance(raw_block, dict)
    ]


def _read_generated_block(raw_block: dict, section_id: str, index: int) -> CanvasBlock:
    block_type = raw_block.get("type")
    if block_type not in _GENERATED_BLOCK_TYPES:
        block_type = "paragraph"
    block_id = safe_generated_id(str(raw_block.get("id") or f"{section_id}-b-{index}"))
    items, option_ids, option_answer = _read_block_options(raw_block)
    answer_index = option_answer
    if answer_index is None:
        answer_index = _answer_index(raw_block.get("answer_index", raw_block.get("correct_index")), len(items))
    component_id = safe_generated_id(str(raw_block.get("component_id") or block_id))
    return CanvasBlock(
        id=block_id,
        type=block_type,
        text=trim_generated_text(str(raw_block.get("text") or raw_block.get("question") or ""), 1200) or None,
        items=items,
        caption=str(raw_block.get("caption") or raw_block.get("title") or "")[:500] or None,
        answer_index=answer_index if block_type in {"quiz", "component"} else None,
        component_id=component_id if block_type == "component" else None,
        component_type=_component_type(raw_block) if block_type == "component" else None,
        component_ref=_component_ref(raw_block.get("component_ref"), component_id) if block_type == "component" else None,
        component_version=_component_version(raw_block.get("component_version", raw_block.get("version"))),
        option_ids=option_ids if block_type == "component" else [],
    )


def _read_block_options(raw_block: dict) -> tuple[list[str], list[str], int | None]:
    options = raw_block.get("options")
    if isinstance(options, list):
        return _read_structured_options(options)
    raw_items = raw_block.get("items", [])
    items = _read_items(raw_items)
    raw_ids = raw_block.get("option_ids", [])
    option_ids = [safe_generated_id(str(item)) for item in raw_ids[: len(items)]] if isinstance(raw_ids, list) else []
    return items, option_ids, None


def _read_structured_options(options: list[object]) -> tuple[list[str], list[str], int | None]:
    items: list[str] = []
    option_ids: list[str] = []
    answer_index = None
    for option in options[:8]:
        if not isinstance(option, dict):
            continue
        text = trim_generated_text(str(option.get("text") or option.get("label") or ""), 240)
        if not text:
            continue
        if option.get("correct") is True:
            answer_index = len(items)
        option_ids.append(safe_generated_id(str(option.get("id") or chr(65 + len(items)))))
        items.append(text)
    return items, option_ids, answer_index


def _read_items(raw_items: object) -> list[str]:
    if not isinstance(raw_items, list):
        return []
    return [trim_generated_text(str(item), 240) for item in raw_items[:8]]


def _fallback_table(section_id: str) -> CanvasBlock:
    return CanvasBlock(
        id=safe_generated_id(f"{section_id}-table"),
        type="table",
        text=(
            "| Action | What to compute |\n"
            "| --- | --- |\n"
            "| Classify | Posterior probability times decision loss |\n"
            "| Reject | Cost of asking for more evidence |\n"
            "| Choose | Lowest expected risk |"
        ),
        caption="Expected-risk table",
    )


def _fallback_checkpoint(section_id: str) -> CanvasBlock:
    return CanvasBlock(
        id=safe_generated_id(f"{section_id}-checkpoint"),
        type="checkpoint",
        caption="Quality gate",
        text="Explain the decision rule, then name which cost or posterior term changes the chosen action.",
    )


def _fallback_quiz(section_id: str) -> CanvasBlock:
    return CanvasBlock(
        id=safe_generated_id(f"{section_id}-quiz"),
        type="quiz",
        caption="Retrieval check",
        text="Which value directly changes the expected-risk threshold?",
        items=["A loss term", "The slide number", "The notation font"],
        answer_index=0,
    )


def _fallback_component(section_id: str) -> CanvasBlock:
    component_id = safe_generated_id(f"{section_id}-risk-check")
    return CanvasBlock(
        id=safe_generated_id(f"{section_id}-component"),
        type="component",
        component_id=component_id,
        component_type="single_choice_quiz",
        component_ref=f"{component_id}.yaml",
        component_version=1,
        caption="Interactive risk check",
        text="Which value directly changes a cost-sensitive classifier decision?",
        items=["The posterior-weighted loss", "The slide number", "The notation font"],
        option_ids=["posterior-loss", "slide-number", "notation-font"],
        answer_index=0,
    )


def _answer_index(value: object, item_count: int) -> int | None:
    if isinstance(value, int) and 0 <= value < item_count:
        return value
    if isinstance(value, str) and value.isdigit():
        index = int(value)
        return index if 0 <= index < item_count else None
    return None


def _component_type(raw_block: dict) -> str:
    value = raw_block.get("component_type") or raw_block.get("kind") or "single_choice_quiz"
    return str(value)[:120]


def _component_ref(value: object, component_id: str) -> str:
    ref = str(value or component_id).strip()
    if not ref or ref.startswith("/") or ".." in ref.split("/"):
        ref = component_id
    if not ref.endswith((".yaml", ".yml", ".json")):
        ref = f"{ref}.yaml"
    return ref[:240]


def _component_version(value: object) -> int | None:
    if isinstance(value, int) and value >= 1:
        return value
    if isinstance(value, str) and value.isdigit() and int(value) >= 1:
        return int(value)
    return None

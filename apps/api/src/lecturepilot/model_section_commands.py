from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.model_generated_ids import (
    safe_generated_id,
    student_section_id,
    trim_generated_text,
)

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
    return CanvasSection(
        id=section_id, title=title, source_ref="student workspace", blocks=blocks[:8]
    )


def _read_generated_blocks(raw_blocks: object, section_id: str) -> list[CanvasBlock]:
    if not isinstance(raw_blocks, list):
        return []
    return [
        _read_generated_block(raw_block, section_id, index)
        for index, raw_block in enumerate(raw_blocks[:10], start=1)
        if isinstance(raw_block, dict)
    ]


def _read_generated_block(raw_block: dict, section_id: str, index: int) -> CanvasBlock:
    coerced = _coerced_quiz_block(raw_block, section_id, index)
    if coerced is not None:
        return coerced
    block_type = raw_block.get("type")
    if block_type not in _GENERATED_BLOCK_TYPES:
        block_type = "paragraph"
    block_id = safe_generated_id(str(raw_block.get("id") or f"{section_id}-b-{index}"))
    items, option_ids, option_answer = _read_block_options(raw_block)
    answer_index = option_answer
    if answer_index is None:
        answer_index = _answer_index(
            raw_block.get("answer_index", raw_block.get("correct_index")), len(items)
        )
    component_id = safe_generated_id(str(raw_block.get("component_id") or block_id))
    return CanvasBlock(
        id=block_id,
        type=block_type,
        text=trim_generated_text(
            str(raw_block.get("text") or raw_block.get("question") or ""), 1200
        )
        or None,
        items=items,
        caption=str(raw_block.get("caption") or raw_block.get("title") or "")[:500] or None,
        answer_index=answer_index if block_type in {"quiz", "component"} else None,
        component_id=component_id if block_type == "component" else None,
        component_type=_component_type(raw_block) if block_type == "component" else None,
        component_ref=_component_ref(raw_block.get("component_ref"), component_id)
        if block_type == "component"
        else None,
        component_version=_component_version(
            raw_block.get("component_version", raw_block.get("version"))
        ),
        option_ids=option_ids if block_type == "component" else [],
    )


def _read_block_options(raw_block: dict) -> tuple[list[str], list[str], int | None]:
    options = raw_block.get("options")
    if isinstance(options, list):
        return _read_structured_options(options)
    raw_items = raw_block.get("items", [])
    items = _read_items(raw_items)
    raw_ids = raw_block.get("option_ids", [])
    option_ids = (
        [safe_generated_id(str(item)) for item in raw_ids[: len(items)]]
        if isinstance(raw_ids, list)
        else []
    )
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


def _coerced_quiz_block(raw_block: dict, section_id: str, index: int) -> CanvasBlock | None:
    text = str(raw_block.get("text") or "")
    if "items:" not in text and "type=quiz" not in text and "--- quiz" not in text:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    question = _field(lines, "text")
    items = _schema_items(lines)
    if not question or len(items) < 2:
        return None
    answer_index = next(
        (item_index for item_index, (_, correct) in enumerate(items) if correct), None
    )
    return CanvasBlock(
        id=safe_generated_id(str(raw_block.get("id") or f"{section_id}-quiz-{index}")),
        type="quiz",
        text=trim_generated_text(question, 1200),
        items=[trim_generated_text(item, 240) for item, _ in items],
        answer_index=answer_index,
    )


def _schema_items(lines: list[str]) -> list[tuple[str, bool]]:
    items: list[tuple[str, bool]] = []
    in_items = False
    current_text = ""
    current_correct = False
    for line in lines:
        if line == "items:":
            in_items = True
            continue
        if not in_items:
            continue
        if line.startswith(("id=", "- id:")):
            if current_text:
                items.append((current_text, current_correct))
            current_text = ""
            current_correct = False
        elif line.startswith(("text=", "text:")):
            current_text = _field_value(line)
        elif line.startswith(("correct=", "correct:")):
            current_correct = _field_value(line).lower() == "true"
        elif not _is_schema_line(line):
            if current_text:
                items.append((current_text, current_correct))
            current_text = line
            current_correct = False
    if current_text:
        items.append((current_text, current_correct))
    return items


def _field(lines: list[str], key: str) -> str:
    for line in lines:
        if line.startswith((f"{key}=", f"{key}:")):
            return _field_value(line)
    return ""


def _field_value(line: str) -> str:
    _, separator, value = line.partition("=")
    if not separator:
        _, _, value = line.partition(":")
    return value.strip().strip('"').strip("'")


def _is_schema_line(line: str) -> bool:
    key = line.partition("=")[0].partition(":")[0].strip()
    return key in {
        "id",
        "section_id",
        "span_id",
        "title",
        "type",
        "text",
        "correct",
    } or line.startswith("---")

from __future__ import annotations

import json

from lecturepilot.canvas_models import CanvasBlock


def component_to_markdown(block: CanvasBlock) -> str:
    payload = {
        "id": block.component_id or block.id,
        "type": block.component_type or "unknown",
        "title": block.caption,
        "prompt": block.text,
        "options": [
            {"id": chr(65 + index), "text": item, "correct": block.answer_index == index}
            for index, item in enumerate(block.items)
        ],
    }
    return (
        f":::component {block.component_id or block.id}\n"
        f"{json.dumps(payload, indent=2, ensure_ascii=False)}\n:::"
    )


def read_component_block(block_id: str, label: str | None, body: str) -> CanvasBlock:
    payload = _component_payload(body)
    options = payload.get("options") if isinstance(payload.get("options"), list) else []
    items, answer_index = _component_options(options)
    return CanvasBlock(
        id=block_id,
        type="component",
        component_id=str(payload.get("id") or label or block_id)[:120],
        component_type=str(payload.get("type") or "unknown")[:120],
        caption=str(payload.get("title") or label or "Interactive component")[:500],
        text=str(payload.get("prompt") or payload.get("text") or "").strip() or None,
        items=items,
        answer_index=answer_index,
    )


def _component_payload(body: str) -> dict:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return {"type": "unknown", "text": body.strip()}
    return payload if isinstance(payload, dict) else {"type": "unknown"}


def _component_options(options: list[object]) -> tuple[list[str], int | None]:
    items: list[str] = []
    answer_index = None
    for option in options[:26]:
        if isinstance(option, dict):
            text = str(option.get("text") or option.get("label") or "").strip()
            is_correct = option.get("correct") is True
        else:
            text = str(option).strip()
            is_correct = False
        if not text:
            continue
        if is_correct:
            answer_index = len(items)
        items.append(text)
    return items, answer_index

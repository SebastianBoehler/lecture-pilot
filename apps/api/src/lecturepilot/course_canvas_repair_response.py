from __future__ import annotations

from typing import Any

from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_response_schema import canvas_block_schema


def repair_patch_response_format() -> dict[str, Any]:
    edit = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "operation": {"type": "string", "const": "replace_block"},
            "section_id": {"type": "string"},
            "block_id": {"type": "string"},
            "blocks": {
                "type": "array",
                "items": canvas_block_schema(),
                "minItems": 1,
            },
        },
        "required": ["operation", "section_id", "block_id", "blocks"],
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "lecturepilot_canvas_repair_patch",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"edits": {"type": "array", "items": edit, "minItems": 1}},
                "required": ["edits"],
            },
        },
    }


def replacement_blocks(payload: dict, *, section_id: str, block_id: str) -> list[dict]:
    edits = payload.get("edits")
    if not isinstance(edits, list) or len(edits) != 1 or not isinstance(edits[0], dict):
        raise CanvasGenerationRepairableError("The repair patch must contain exactly one edit.")
    edit = edits[0]
    if (
        edit.get("operation") != "replace_block"
        or edit.get("section_id") != section_id
        or edit.get("block_id") != block_id
    ):
        raise CanvasGenerationRepairableError(
            "The repair patch must target the requested section and block."
        )
    blocks = edit.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise CanvasGenerationRepairableError("The repair patch returned no replacement blocks.")
    return blocks

from __future__ import annotations

from lecturepilot.canvas_models import CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError


def block_items(raw_block: dict) -> list:
    if isinstance(raw_block.get("items"), list):
        return raw_block["items"]
    if isinstance(raw_block.get("content"), list):
        return raw_block["content"]
    return []


def answer_index(raw_block: dict) -> int:
    items = block_items(raw_block)[:26]
    value = raw_block.get("answer_index", raw_block.get("correct_index"))
    if not isinstance(value, int) or not 0 <= value < len(items):
        raise CanvasGenerationRepairableError(
            "Quiz blocks need an explicit answer_index within the answer options."
        )
    return value


def allowed_assets(section: CanvasSection) -> dict[str, str | None]:
    return {
        block.asset_path: block.asset_url
        for block in section.blocks
        if block.type in {"asset", "video"} and block.asset_path
    }


def safe_section_id(value: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "-" for char in value)
    return "-".join(part for part in safe.split("-") if part)[:120] or "learning-section"

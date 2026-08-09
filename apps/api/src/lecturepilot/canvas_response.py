from __future__ import annotations

from lecturepilot.canvas_models import CanvasDocument


def learner_canvas_payload(document: CanvasDocument) -> dict:
    """Serialize a learner canvas without server-owned quiz answer keys."""
    payload = document.model_dump(exclude={"workspace_path"})
    for section in payload.get("sections", []):
        for block in section.get("blocks", []):
            block.pop("answer_index", None)
    return payload

from __future__ import annotations

from lecturepilot.canvas_models import CanvasDocument


class PlannedPayload(dict):
    warnings: list[str]


def planned_payload(payload: dict, *, finish_reason: str) -> PlannedPayload:
    result = PlannedPayload(payload)
    result.warnings = finish_reason_warnings(finish_reason)
    return result


def finish_reason_warnings(finish_reason: str) -> list[str]:
    if not finish_reason or finish_reason in {"stop", "tool_calls"}:
        return []
    return [
        f"Planner model finished with reason '{finish_reason}'. Review this draft before publishing."
    ]


def with_payload_warnings(document: CanvasDocument, payload: dict) -> CanvasDocument:
    warnings = getattr(payload, "warnings", [])
    if not warnings:
        return document
    return document.model_copy(update={"warnings": [*document.warnings, *warnings]})

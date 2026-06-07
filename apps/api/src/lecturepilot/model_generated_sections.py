from __future__ import annotations

import re
from datetime import UTC, datetime

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.models import AgentTurnInput, CanvasCommand


def fallback_generated_command(turn: AgentTurnInput, focus_section_id: str) -> CanvasCommand | None:
    message = turn.message.lower()
    has_action = any(word in message for word in ("add", "create", "generate", "make", "write", "insert"))
    has_target = any(word in message for word in ("canvas", "section", "note", "infographic", "diagram"))
    has_explicit_example = "example" in message and has_action
    if not has_action or not (has_target or has_explicit_example):
        return None
    title = _generated_title(turn.message)
    section_id = _student_section_id(title)
    section = CanvasSection(
        id=section_id,
        title=title,
        source_ref="student workspace",
        blocks=[
            CanvasBlock(
                id=_safe_generated_id(f"{section_id}-callout"),
                type="callout",
                text=f"Generated learner note anchored in {_section_title(turn, focus_section_id)}.",
            ),
            CanvasBlock(
                id=_safe_generated_id(f"{section_id}-steps"),
                type="list",
                items=_generated_items(turn.message),
            ),
            CanvasBlock(
                id=_safe_generated_id(f"{section_id}-check"),
                type="paragraph",
                text="Use this personalized explanation, then answer the tutor's next check in your own words.",
            ),
        ],
    )
    return CanvasCommand(type="append_section", section_id=section.id, section=section)


def _generated_title(message: str) -> str:
    lowered = message.lower()
    if "soccer" in lowered or "football" in lowered:
        return "Soccer scouting example"
    if "infographic" in lowered or "diagram" in lowered:
        return "Generated concept infographic"
    if "example" in lowered:
        return "Generated learning example"
    return "Generated learning note"


def _generated_items(message: str) -> list[str]:
    lowered = message.lower()
    if "bayes" in lowered or "posterior" in lowered:
        return [
            "Prior: what you believed before the new evidence.",
            "Likelihood: how compatible the evidence is with each class.",
            "Posterior: the updated belief after applying Bayes' rule.",
            "Decision: choose the action after considering risk or cost.",
        ]
    return [
        "Locate the source concept in the focused lecture section.",
        "Restate the concept using the student's requested context.",
        "Connect the example back to the formal learning goal.",
    ]


def _section_title(turn: AgentTurnInput, section_id: str) -> str:
    if turn.canvas_context is None:
        return "the current lecture section"
    for section in turn.canvas_context.sections:
        if section.id == section_id:
            return section.title
    return "the current lecture section"


def _student_section_id(value: str) -> str:
    safe = _safe_generated_id(value)
    if safe.startswith("student-"):
        return safe
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"student-{safe[:80]}-{suffix}"


def _safe_generated_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.lower()).strip("-")
    return (safe or "generated-note")[:120]

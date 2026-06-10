from __future__ import annotations

import re
from datetime import UTC, datetime

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.models import AgentTurnInput, CanvasCommand


def fallback_generated_command(turn: AgentTurnInput, focus_section_id: str) -> CanvasCommand | None:
    message = turn.message.lower()
    has_action = any(
        word in message
        for word in (
            "add",
            "append",
            "create",
            "edit",
            "extend",
            "generate",
            "insert",
            "make",
            "new",
            "update",
            "write",
        )
    )
    has_target = any(
        word in message
        for word in (
            "canvas",
            "chart",
            "diagram",
            "graph",
            "infographic",
            "note",
            "plot",
            "section",
            "table",
            "visual",
        )
    )
    has_explicit_example = "example" in message and has_action
    if not has_action or not (has_target or has_explicit_example):
        return None
    title = _generated_title(turn.message)
    section_id = _student_section_id(title)
    blocks = [
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
        *_practice_blocks(turn.message, section_id),
        CanvasBlock(
            id=_safe_generated_id(f"{section_id}-check"),
            type="paragraph",
            text="Use this personalized explanation, then answer the tutor's next check in your own words.",
        ),
    ]
    section = CanvasSection(
        id=section_id,
        title=title,
        source_ref="student workspace",
        blocks=blocks,
    )
    return CanvasCommand(type="append_section", section_id=section.id, section=section)


def _generated_title(message: str) -> str:
    lowered = message.lower()
    if "soccer" in lowered or "football" in lowered:
        return "Soccer scouting example"
    if "infographic" in lowered or "diagram" in lowered:
        return "Generated concept infographic"
    if "plot" in lowered or "chart" in lowered or "graph" in lowered:
        return "Generated concept plot"
    if "table" in lowered:
        return "Generated comparison table"
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
    if any(word in lowered for word in ("risk", "loss", "false negative", "false positive", "threshold")):
        return [
            "Rows: possible actions such as classify positive, classify negative, or reject.",
            "Columns: possible true states such as class present or class absent.",
            "Each cell: the cost of that action when the true state occurs.",
            "Decision: multiply each cost by the posterior probability and choose the lowest expected risk.",
        ]
    return [
        "Locate the source concept in the focused lecture section.",
        "Restate the concept using the student's requested context.",
        "Connect the example back to the formal learning goal.",
    ]


def _practice_blocks(message: str, section_id: str) -> list[CanvasBlock]:
    lowered = message.lower()
    blocks: list[CanvasBlock] = []
    if "checkpoint" in lowered or "gate" in lowered:
        blocks.append(
            CanvasBlock(
                id=_safe_generated_id(f"{section_id}-checkpoint"),
                type="checkpoint",
                caption="Quality gate",
                text="State the concept, apply it to one concrete case, and explain the failure mode the formula prevents.",
            )
        )
    if "quiz" in lowered:
        blocks.append(
            CanvasBlock(
                id=_safe_generated_id(f"{section_id}-quiz"),
                type="quiz",
                caption="Retrieval check",
                text="Which piece of evidence would change the expected-risk decision most directly?",
                items=["The posterior probability", "The typography of the notes", "The lecture date"],
                answer_index=0,
            )
        )
    return blocks


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

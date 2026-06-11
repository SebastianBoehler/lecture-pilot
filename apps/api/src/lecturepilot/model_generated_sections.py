from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.model_generated_ids import safe_generated_id, student_section_id
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
            "component",
            "diagram",
            "graph",
            "infographic",
            "interactive",
            "note",
            "plot",
            "quiz",
            "section",
            "table",
            "visual",
        )
    )
    has_explicit_example = "example" in message and has_action
    if not has_action or not (has_target or has_explicit_example):
        return None
    title = _generated_title(turn.message)
    section_id = student_section_id(title)
    blocks = [
        CanvasBlock(
            id=safe_generated_id(f"{section_id}-callout"),
            type="callout",
            text=f"Generated learner note anchored in {_section_title(turn, focus_section_id)}.",
        ),
        CanvasBlock(
            id=safe_generated_id(f"{section_id}-steps"),
            type="list",
            items=_generated_items(turn.message),
        ),
        *_practice_blocks(turn.message, section_id),
        CanvasBlock(
            id=safe_generated_id(f"{section_id}-check"),
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
    if "component" in lowered or "interactive" in lowered:
        component_id = safe_generated_id(f"{section_id}-risk-check")
        blocks.append(
            CanvasBlock(
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
        )
    if "checkpoint" in lowered or "gate" in lowered:
        blocks.append(
            CanvasBlock(
                id=safe_generated_id(f"{section_id}-checkpoint"),
                type="checkpoint",
                caption="Quality gate",
                text="State the concept, apply it to one concrete case, and explain the failure mode the formula prevents.",
            )
        )
    if "quiz" in lowered:
        blocks.append(
            CanvasBlock(
                id=safe_generated_id(f"{section_id}-quiz"),
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

from __future__ import annotations

from dataclasses import dataclass

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    AttendanceStatus,
    CanvasCommand,
    QualityGateDecision,
    QualityGateStatus,
)
from lecturepilot.learning_gates import GateEvaluation, GateTarget, evaluate_learning_gate


LOCAL_PREVIEW_USER_ID = "local-preview-user"


@dataclass(frozen=True)
class TopicTarget:
    section_id: str
    span_id: str
    highlight_text: str


def run_local_preview_turn(turn: AgentTurnInput) -> AgentTurnResult:
    learning_mode = _learning_mode(turn)
    evidence = evaluate_learning_gate(turn.lecture_id, turn.message)
    if _asks_for_soccer_example(turn.message):
        section = _soccer_bayes_section()
        return AgentTurnResult(
            message=(
                f"{learning_mode} I added a soccer scouting example to your personal canvas "
                "and focused it. Use it to explain posterior, risk, and the final decision."
            ),
            canvas_commands=[
                CanvasCommand(type="append_section", section_id=section.id, section=section),
                CanvasCommand(type="focus_section", section_id=section.id),
                CanvasCommand(
                    type="highlight_span",
                    section_id=section.id,
                    span_id=f"{section.id}-p-1",
                    highlight_text="evidence X",
                ),
            ],
            quality_gate=QualityGateDecision(
                gate_id=evidence.spec.gate_id,
                status=QualityGateStatus.NEEDS_EVIDENCE,
                reason="The learner asked for a personalized transfer example.",
                next_prompt=f"Use the example to add evidence for: {evidence.next_missing_label}.",
            ),
            model="local-guided-preview",
        )

    if evidence.is_complete:
        target = _gate_target(turn, evidence.spec.passed_target)
        return AgentTurnResult(
            message=(
                f"Gate passed: you connected the required ideas for {evidence.spec.title}. "
                "I focused the next application point so you can transfer it to one example."
            ),
            canvas_commands=[
                CanvasCommand(type="focus_section", section_id=target.section_id),
                CanvasCommand(
                    type="highlight_span",
                    section_id=target.section_id,
                    span_id=target.span_id,
                    highlight_text=target.highlight_text,
                ),
            ],
            quality_gate=QualityGateDecision(
                gate_id=evidence.spec.gate_id,
                status=QualityGateStatus.PASSED,
                reason=f"The learner supplied evidence for {evidence.spec.title}.",
                next_prompt="Apply the decision rule to a concrete classification case.",
            ),
            model="local-guided-preview",
        )

    missing = ", ".join(evidence.missing_labels)
    target = _topic_target(turn)
    return AgentTurnResult(
        message=_pending_gate_message(turn, learning_mode, missing, evidence),
        canvas_commands=[
            CanvasCommand(type="focus_section", section_id=target.section_id),
            CanvasCommand(
                type="highlight_span",
                section_id=target.section_id,
                span_id=target.span_id,
                highlight_text=target.highlight_text,
            ),
        ],
        quality_gate=QualityGateDecision(
            gate_id=evidence.spec.gate_id,
            status=QualityGateStatus.NEEDS_EVIDENCE,
            reason=f"Missing evidence: {missing}.",
            next_prompt=f"Add one concrete sentence for: {evidence.next_missing_label}.",
        ),
        model="local-guided-preview",
    )


def _mentions_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _pending_gate_message(
    turn: AgentTurnInput,
    learning_mode: str,
    missing: str,
    evidence: GateEvaluation,
) -> str:
    next_check = evidence.next_missing_label
    if turn.attendance == AttendanceStatus.PRESENT:
        return (
            f"{learning_mode} Feedback: your answer is not complete yet. Gate pending; "
            f"missing evidence: {missing}. I focused the supporting canvas text. Next check: "
            f"add {next_check} with one concrete example or worked consequence."
        )
    if turn.attendance == AttendanceStatus.ABSENT:
        return (
            f"{learning_mode} Start with this section, then move toward the gate in small steps. "
            f"First work on {next_check}. Use the highlighted text, then answer with one "
            f"sentence before we continue. Gate pending; missing evidence: {missing}."
        )
    return (
        f"{learning_mode} I focused the most relevant canvas section to diagnose the gap. "
        f"Gate pending; missing evidence: {missing}. First add {next_check}."
    )


def _topic_target(turn: AgentTurnInput) -> TopicTarget:
    normalized = turn.message.lower()
    if _mentions_any(
        normalized,
        ("risk", "cost", "loss", "false positive", "false negative", "threshold", "reject"),
    ):
        return _canvas_target(turn, ("risk", "loss", "cost", "boundar"), "cost") or TopicTarget(
            "losses-and-risks",
            "losses-and-risks-list",
            "costly",
        )
    if _mentions_any(normalized, ("spam", "naive", "filter", "independence")):
        return _canvas_target(turn, ("naive", "spam", "text"), "Naive Bayes") or TopicTarget(
            "naive-bayes-classifiers",
            "naive-bayes-classifiers-p-1",
            "Naive Bayes",
        )
    if _mentions_any(normalized, ("decision", "classif", "predict", "choose")):
        return _canvas_target(turn, ("decision", "risk", "classif"), "decision") or TopicTarget(
            "losses-and-risks",
            "losses-and-risks-list",
            "decision",
        )
    if _mentions_any(normalized, ("posterior", "prior", "likelihood", "evidence", "formula", "p(c|x")):
        return _canvas_target(turn, ("bayes", "conditional", "formula"), "probability") or TopicTarget(
            "bayes-formula",
            "bayes-formula-list",
            "probability",
        )
    default = evaluate_learning_gate(turn.lecture_id, turn.message).spec.pending_target
    return _focused_canvas_target(turn) or _topic_target_from_gate(default)


def _gate_target(turn: AgentTurnInput, target: GateTarget) -> TopicTarget:
    if turn.canvas_context is None:
        return _topic_target_from_gate(target)
    for section in turn.canvas_context.sections:
        if section.id == target.section_id:
            return TopicTarget(section.id, _first_teaching_block_id(section), target.highlight_text)
    return _topic_target_from_gate(target)


def _topic_target_from_gate(target: GateTarget) -> TopicTarget:
    return TopicTarget(target.section_id, target.span_id, target.highlight_text)


def _canvas_target(
    turn: AgentTurnInput,
    needles: tuple[str, ...],
    highlight_text: str,
) -> TopicTarget | None:
    if turn.canvas_context is None:
        return None
    for section in turn.canvas_context.sections:
        haystack = f"{section.id} {section.title}".lower()
        if not any(needle in haystack for needle in needles):
            continue
        return TopicTarget(section.id, _first_teaching_block_id(section), highlight_text)
    return None


def _focused_canvas_target(turn: AgentTurnInput) -> TopicTarget | None:
    if turn.canvas_context is None:
        return None
    focused = turn.canvas_state.focused_section_id
    for section in turn.canvas_context.sections:
        if section.id == focused:
            return TopicTarget(section.id, _first_teaching_block_id(section), "key idea")
    if turn.canvas_context.sections:
        section = turn.canvas_context.sections[0]
        return TopicTarget(section.id, _first_teaching_block_id(section), "key idea")
    return None


def _first_teaching_block_id(section) -> str:
    for block in section.blocks:
        if block.type in {"paragraph", "list", "math", "callout"}:
            return block.id
    return section.blocks[0].id if section.blocks else f"{section.id}-heading"


def _asks_for_soccer_example(message: str) -> bool:
    normalized = message.lower()
    return _mentions_any(normalized, ("soccer", "football", "spieler", "verein"))


def _learning_mode(turn: AgentTurnInput) -> str:
    if turn.attendance == AttendanceStatus.PRESENT:
        return (
            "Verification mode: you marked yourself present, so I will verify your knowledge "
            "and give feedback before reteaching."
        )
    if turn.attendance == AttendanceStatus.ABSENT:
        return (
            "Guided walkthrough mode: you marked yourself absent, so I will teach the material "
            "step by step toward the quality gate."
        )
    return "Diagnostic mode: attendance is unknown, so I will first locate the missing concept."


def _soccer_bayes_section() -> CanvasSection:
    return CanvasSection(
        id="student-soccer-bayes-example",
        title="Soccer scouting example",
        source_ref="student workspace",
        blocks=[
            CanvasBlock(
                id="student-soccer-bayes-example-p-1",
                type="paragraph",
                text=(
                    "Treat a scouting report as evidence X and the hidden event C as whether "
                    "a player will fit the team. Bayes updates the prior belief into a posterior "
                    "after observing the report, match data, and training signals."
                ),
            ),
            CanvasBlock(
                id="student-soccer-bayes-example-list",
                type="list",
                items=[
                    "Prior: the base chance that a player succeeds before the new report.",
                    "Likelihood: how probable this report is if the player truly fits.",
                    "Evidence: how common this report is across all players.",
                    "Decision risk: missing a strong player and signing a poor fit have different costs.",
                ],
            ),
        ],
    )

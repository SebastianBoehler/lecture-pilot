from __future__ import annotations

from lecturepilot.models import (
    AgentTurnInput,
    CanvasCommand,
    QualityGateDecision,
    QualityGateStatus,
)
from lecturepilot.coaching_assistance import NextCheck
from lecturepilot.providers import ProviderConfigurationError


def canvas_context(turn: AgentTurnInput) -> str:
    document = turn.canvas_context
    if document is None:
        return "Canvas context: unavailable. Use the current section id only."
    lines = [
        f"Canvas title: {document.title}",
        f"Canvas source: {document.source_ref}",
        "Allowed canvas targets:",
    ]
    for section in document.sections:
        lines.append(f"- section_id={section.id}; title={section.title}")
        for block in section.blocks[:5]:
            excerpt = _block_excerpt(
                block.type, block.text, block.items, block.caption, block.asset_path
            )
            if excerpt:
                lines.append(f"  span_id={block.id}; type={block.type}; text={excerpt}")
    return _trim_text("\n".join(lines), 9000)


def read_quality_gate(payload: dict, turn: AgentTurnInput) -> QualityGateDecision | None:
    active_gate = turn.active_gate
    if active_gate is None:
        return None
    raw_gate = payload.get("quality_gate")
    if not isinstance(raw_gate, dict):
        raise ProviderConfigurationError("Model omitted the active quality-gate decision.")
    gate = QualityGateDecision.model_validate(raw_gate)
    return validate_quality_gate_decision(gate, turn)


def assessment_required(turn: AgentTurnInput) -> bool:
    active_gate = turn.active_gate
    context = turn.coaching_context
    return (
        active_gate is not None
        and context.pending_check_gate_id == active_gate.id
        and context.pending_check_gate_revision == active_gate.revision
        and context.pending_check_issued_at is not None
    )


def validate_quality_gate_decision(
    decision: QualityGateDecision | None,
    turn: AgentTurnInput,
) -> QualityGateDecision | None:
    active_gate = turn.active_gate
    bound = assessment_required(turn)
    if active_gate is None:
        if decision is not None:
            raise ProviderConfigurationError(
                "Model returned a quality gate without an active gate."
            )
        return None
    if not bound:
        if decision is not None:
            raise ProviderConfigurationError("Model assessed a turn without a bound pending check.")
        return None
    if decision is None:
        raise ProviderConfigurationError("Model omitted the bound quality-gate assessment.")
    if decision.gate_id != active_gate.id or decision.gate_revision != active_gate.revision:
        raise ProviderConfigurationError("Model quality gate does not match the active contract.")
    allowed = {criterion.id for criterion in active_gate.evidence_criteria}
    required = [criterion.id for criterion in active_gate.evidence_criteria if criterion.required]
    if len(set(decision.evidence_ids)) != len(decision.evidence_ids) or len(
        set(decision.missing_evidence_ids)
    ) != len(decision.missing_evidence_ids):
        raise ProviderConfigurationError("Model quality-gate evidence IDs must be unique.")
    if not set(decision.evidence_ids + decision.missing_evidence_ids) <= allowed:
        raise ProviderConfigurationError("Model returned unknown quality-gate evidence IDs.")
    evidence = decision.evidence_ids
    missing = [evidence_id for evidence_id in required if evidence_id not in evidence]
    if decision.missing_evidence_ids != missing:
        raise ProviderConfigurationError("Model missing-evidence IDs do not match the gate rubric.")
    if decision.status == QualityGateStatus.PASSED and missing:
        raise ProviderConfigurationError("Model passed a gate without all required evidence.")
    return decision


def validate_next_check(next_check: NextCheck | None, turn: AgentTurnInput) -> None:
    gate = turn.active_gate
    if next_check is None:
        return
    if gate is None:
        raise ProviderConfigurationError("Model returned a next check without an active gate.")
    if next_check.gate_id != gate.id or next_check.gate_revision != gate.revision:
        raise ProviderConfigurationError("Model next check does not match the active contract.")


def resolve_provider_canvas_commands(
    commands: list[CanvasCommand], turn: AgentTurnInput
) -> list[CanvasCommand]:
    focus = [command for command in commands if command.type == "focus_section"]
    highlights = [command for command in commands if command.type == "highlight_span"]
    if len(focus) != 1 or len(highlights) != 1:
        raise ProviderConfigurationError(
            "Model response requires exactly one focus and one highlight command."
        )
    allowed_sections = _allowed_section_ids(turn)
    allowed_spans = _allowed_span_ids(turn)
    if not allowed_sections or not allowed_spans:
        raise ProviderConfigurationError("Canvas navigation cannot be validated without context.")
    if focus[0].section_id not in allowed_sections:
        raise ProviderConfigurationError("Model focus target is not in the canvas context.")
    highlight = highlights[0]
    if highlight.span_id not in allowed_spans:
        raise ProviderConfigurationError("Model highlight target is not in the canvas context.")
    expected_section = _section_for_span(turn, highlight.span_id or "")
    return [
        command.model_copy(update={"section_id": expected_section})
        if command is highlight
        else command
        for command in commands
    ]


def _allowed_section_ids(turn: AgentTurnInput) -> set[str]:
    if turn.canvas_context is None:
        return set()
    return {section.id for section in turn.canvas_context.sections}


def _allowed_span_ids(turn: AgentTurnInput) -> set[str]:
    if turn.canvas_context is None:
        return set()
    return {block.id for section in turn.canvas_context.sections for block in section.blocks}


def _section_for_span(turn: AgentTurnInput, span_id: str) -> str | None:
    if turn.canvas_context is None:
        return None
    for section in turn.canvas_context.sections:
        if any(block.id == span_id for block in section.blocks):
            return section.id
    return None


def _block_excerpt(
    block_type: str, text: str | None, items: list[str], caption: str | None, asset_path: str | None
) -> str:
    if block_type == "asset":
        return _trim_text(caption or asset_path or "asset", 180)
    if items:
        return _trim_text("; ".join(items[:5]), 260)
    return _trim_text(text or "", 260)


def _trim_text(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."

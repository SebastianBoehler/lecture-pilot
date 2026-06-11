from __future__ import annotations

import re

from lecturepilot.model_generated_sections import fallback_generated_command
from lecturepilot.model_section_commands import (
    ensure_requested_learning_blocks,
    read_generated_section,
)
from lecturepilot.models import AgentTurnInput, CanvasCommand, QualityGateDecision, QualityGateStatus

_SAFE_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,119}")


def canvas_context(turn: AgentTurnInput) -> str:
    document = turn.canvas_context
    if document is None:
        return "Canvas context: unavailable. Use the current section id only."
    lines = [f"Canvas title: {document.title}", f"Canvas source: {document.source_ref}", "Allowed canvas targets:"]
    for section in document.sections:
        lines.append(f"- section_id={section.id}; title={section.title}")
        for block in section.blocks[:5]:
            excerpt = _block_excerpt(block.type, block.text, block.items, block.caption, block.asset_path)
            if excerpt:
                lines.append(f"  span_id={block.id}; type={block.type}; text={excerpt}")
    return _trim_text("\n".join(lines), 9000)


def read_canvas_commands(payload: dict, turn: AgentTurnInput) -> list[CanvasCommand]:
    commands: list[CanvasCommand] = []
    raw_commands = payload.get("canvas_commands")
    if isinstance(raw_commands, list):
        commands.extend(_read_command(item, turn) for item in raw_commands if isinstance(item, dict))
    if not any(command.type in {"append_section", "update_section"} for command in commands):
        fallback_generated = fallback_generated_command(turn, _default_section_id(turn))
        if fallback_generated is not None:
            commands.insert(0, fallback_generated)
    commands = [_ensure_requested_learning_blocks(command, turn) for command in commands]
    focus_id = _read_section_id(payload.get("focus_section_id"), turn)
    if not any(command.type == "focus_section" for command in commands):
        commands.insert(0, CanvasCommand(type="focus_section", section_id=focus_id))
    legacy_highlight = _read_highlight_command(payload, turn)
    if legacy_highlight is not None:
        commands.append(legacy_highlight)
    return _normalize_commands([command for command in commands if command.section_id], focus_id, turn)


def read_quality_gate(payload: dict, turn: AgentTurnInput) -> QualityGateDecision:
    expected_gate_id = "bayes-decision-check" if turn.lecture_id == "lecture-03" else "lecture-learning-outcome-check"
    raw_gate = payload.get("quality_gate")
    if not isinstance(raw_gate, dict):
        return QualityGateDecision(
            gate_id=expected_gate_id,
            status=QualityGateStatus.NOT_ASSESSED,
            reason="The model did not return a quality gate decision.",
            next_prompt="Answer the current skill check in one sentence.",
        )
    gate = QualityGateDecision.model_validate(raw_gate)
    return gate.model_copy(update={"gate_id": expected_gate_id})


def _read_command(raw_command: dict, turn: AgentTurnInput) -> CanvasCommand:
    command_type = raw_command.get("type")
    if command_type == "highlight_span":
        return _read_highlight_command(raw_command, turn) or _fallback_focus(turn)
    if command_type in {"append_section", "update_section"}:
        section = read_generated_section(raw_command)
        if section is not None:
            return CanvasCommand(type=command_type, section_id=section.id, section=section)
    return CanvasCommand(type="focus_section", section_id=_read_section_id(raw_command.get("section_id"), turn))


def _ensure_requested_learning_blocks(command: CanvasCommand, turn: AgentTurnInput) -> CanvasCommand:
    return ensure_requested_learning_blocks(command, turn)


def _read_highlight_command(raw_command: dict, turn: AgentTurnInput) -> CanvasCommand | None:
    span_id = raw_command.get("span_id") or raw_command.get("block_id") or raw_command.get("highlight_span_id")
    if not isinstance(span_id, str) or not _is_valid_span_id(span_id, turn):
        return None
    inferred_section = _section_for_span(turn, span_id)
    section_id = inferred_section or _read_section_id(raw_command.get("section_id"), turn)
    highlight_text = raw_command.get("highlight_text")
    return CanvasCommand(
        type="highlight_span",
        section_id=section_id,
        span_id=span_id,
        highlight_text=_trim_text(highlight_text, 160) if isinstance(highlight_text, str) else None,
    )


def _read_section_id(requested: object, turn: AgentTurnInput) -> str:
    if isinstance(requested, str) and _SAFE_ID_RE.fullmatch(requested):
        allowed = _allowed_section_ids(turn)
        if not allowed or requested in allowed:
            return requested
    return _default_section_id(turn)


def _default_section_id(turn: AgentTurnInput) -> str:
    current = turn.canvas_state.focused_section_id
    if current and _SAFE_ID_RE.fullmatch(current):
        allowed = _allowed_section_ids(turn)
        if not allowed or current in allowed:
            return current
    if turn.canvas_context and turn.canvas_context.sections:
        return turn.canvas_context.sections[0].id
    return "bayesian-decision-theory-the-aim"


def _normalize_commands(commands: list[CanvasCommand], fallback_focus_id: str, turn: AgentTurnInput) -> list[CanvasCommand]:
    clean = _dedupe_commands(commands)
    generated = [command for command in clean if command.type in {"append_section", "update_section"}]
    focus = next((command for command in clean if command.type == "focus_section"), None)
    if generated:
        focus = CanvasCommand(type="focus_section", section_id=generated[0].section_id)
    focus = focus or CanvasCommand(type="focus_section", section_id=fallback_focus_id)
    highlights = [command for command in clean if command.type == "highlight_span"]
    if not highlights:
        fallback_highlight = _fallback_highlight(turn, focus.section_id or fallback_focus_id)
        if fallback_highlight is not None:
            highlights.append(fallback_highlight)
    return [*generated[:1], focus, *highlights[:1]]


def _fallback_focus(turn: AgentTurnInput) -> CanvasCommand:
    return CanvasCommand(type="focus_section", section_id=_default_section_id(turn))


def _fallback_highlight(turn: AgentTurnInput, section_id: str) -> CanvasCommand | None:
    if turn.canvas_context is None:
        return None
    for section in turn.canvas_context.sections:
        if section.id != section_id:
            continue
        for block in section.blocks:
            if block.type in {"paragraph", "list", "math", "callout"}:
                source_text = block.items[0] if block.items else block.text
                return CanvasCommand(
                    type="highlight_span",
                    section_id=section.id,
                    span_id=block.id,
                    highlight_text=_trim_text(source_text or "", 100) or None,
                )
    return None


def _allowed_section_ids(turn: AgentTurnInput) -> set[str]:
    if turn.canvas_context is None:
        return set()
    return {section.id for section in turn.canvas_context.sections}


def _allowed_span_ids(turn: AgentTurnInput) -> set[str]:
    if turn.canvas_context is None:
        return set()
    return {block.id for section in turn.canvas_context.sections for block in section.blocks}


def _is_valid_span_id(span_id: str, turn: AgentTurnInput) -> bool:
    if not _SAFE_ID_RE.fullmatch(span_id):
        return False
    allowed = _allowed_span_ids(turn)
    return not allowed or span_id in allowed


def _section_for_span(turn: AgentTurnInput, span_id: str) -> str | None:
    if turn.canvas_context is None:
        return None
    for section in turn.canvas_context.sections:
        if any(block.id == span_id for block in section.blocks):
            return section.id
    return None


def _dedupe_commands(commands: list[CanvasCommand]) -> list[CanvasCommand]:
    result: list[CanvasCommand] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    for command in commands:
        key = (command.type, command.section_id, command.span_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(command)
    return result


def _block_excerpt(block_type: str, text: str | None, items: list[str], caption: str | None, asset_path: str | None) -> str:
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

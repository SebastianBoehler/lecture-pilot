from __future__ import annotations

from typing import TYPE_CHECKING

from lecturepilot.model_commands import validate_quality_gate_decision
from lecturepilot.models import AgentTurnInput, AgentTurnResult, CanvasCommand

if TYPE_CHECKING:
    from lecturepilot.agent_tool_executor import AgentToolExecutor


def dedupe_commands(commands: list[CanvasCommand]) -> list[CanvasCommand]:
    result: list[CanvasCommand] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    for command in commands:
        key = (command.type, command.section_id, command.span_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(command)
    return result


def without_generated_section_commands(result: AgentTurnResult) -> AgentTurnResult:
    commands = [
        command
        for command in result.canvas_commands
        if command.type not in {"append_section", "update_section"}
    ]
    return result.model_copy(update={"canvas_commands": commands})


def merge_tool_outputs(
    result: AgentTurnResult,
    tool_executor: AgentToolExecutor,
) -> AgentTurnResult:
    commands = dedupe_commands([*result.canvas_commands, *tool_executor.canvas_update_commands()])
    return result.model_copy(update={"canvas_commands": commands})


def enforce_active_gate_contract(result: AgentTurnResult, turn: AgentTurnInput) -> AgentTurnResult:
    return result.model_copy(
        update={"quality_gate": validate_quality_gate_decision(result.quality_gate, turn)}
    )

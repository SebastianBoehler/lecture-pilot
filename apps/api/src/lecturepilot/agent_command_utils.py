from __future__ import annotations

from typing import TYPE_CHECKING

from lecturepilot.models import AgentTurnResult, CanvasCommand

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
    gate = tool_executor.gate or result.quality_gate
    return result.model_copy(update={"canvas_commands": commands, "quality_gate": gate})

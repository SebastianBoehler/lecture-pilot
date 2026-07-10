from __future__ import annotations

from lecturepilot.models import CanvasCommand


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

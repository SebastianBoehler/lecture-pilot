from typing import Any

from lecturepilot.models import AgentTurnInput


def constrain_tutor_response(schema: dict[str, Any], turn: AgentTurnInput) -> None:
    """Match provider navigation and text bounds to backend validation."""
    sections = turn.canvas_context.sections if turn.canvas_context else []
    command = schema["properties"]["canvas_commands"]["items"]["properties"]
    command["section_id"]["enum"] = [None, *dict.fromkeys(s.id for s in sections)]
    command["span_id"]["enum"] = [
        None,
        *dict.fromkeys(block.id for section in sections for block in section.blocks),
    ]
    command["highlight_text"]["maxLength"] = 160
    schema["properties"]["session_goal"]["maxLength"] = 500
    schema["properties"]["message"]["minLength"] = 1

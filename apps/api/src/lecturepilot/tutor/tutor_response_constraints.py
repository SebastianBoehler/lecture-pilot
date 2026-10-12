from typing import Any


def constrain_tutor_response(schema: dict[str, Any]) -> None:
    """Match provider text bounds to backend validation.

    Navigation ids stay out of the schema: the schema precedes the prompt in provider prefix
    caches, and learner-owned section ids differ per learner. ``agent_result_from_content``
    rejects any id outside the turn's canvas (published or learner-owned) and the output
    validator asks the model to repair it, so unknown targets still fail closed.
    """
    command = schema["properties"]["canvas_commands"]["items"]["properties"]
    command["section_id"]["maxLength"] = 120
    command["span_id"]["maxLength"] = 120
    command["highlight_text"]["maxLength"] = 160
    schema["properties"]["session_goal"]["maxLength"] = 500
    schema["properties"]["message"]["minLength"] = 1

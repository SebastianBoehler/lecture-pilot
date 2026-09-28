"""Classify native no-action failures without retrying invalid tool outputs."""

from pydantic_ai.messages import ModelResponse, ToolCallPart


def no_action_response_exhausted(error, messages):
    if str(error) != "Exceeded maximum output retries (3)" or not messages:
        return False
    response = messages[-1]
    return (
        isinstance(response, ModelResponse)
        and response.finish_reason not in {"length", "content_filter"}
        and not any(isinstance(part, ToolCallPart) for part in response.parts)
    )

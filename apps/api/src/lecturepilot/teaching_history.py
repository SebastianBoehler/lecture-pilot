"""Compact superseded implementation context without editing durable history."""

from lecturepilot.authoring_history import compact_authoring_history
from dataclasses import replace

from pydantic_ai.messages import ModelRequest, ToolReturnPart, UserPromptPart


def compact_teaching_history(messages):
    messages = compact_authoring_history(messages)
    latest_prompts, latest_review = {}, None
    for i, message in enumerate(messages):
        if not isinstance(message, ModelRequest):
            continue
        for j, part in enumerate(message.parts):
            key = _context(part)
            if key is not None:
                latest_prompts[key] = (i, j)
            if isinstance(part, ToolReturnPart) and part.tool_name == "validate":
                latest_review = (i, j)

    def compact(part, position):
        key = _context(part)
        if key is not None and latest_prompts[key] != position:
            return replace(
                part,
                content="Superseded by the latest identical source and approved intent context.",
            )
        if (
            isinstance(part, ToolReturnPart)
            and part.tool_name == "validate"
            and position != latest_review
        ):
            return replace(
                part,
                content="Superseded by the latest implementation review. Read the current saved targets and review.",
            )
        return part

    return [
        replace(message, parts=[compact(part, (i, j)) for j, part in enumerate(message.parts)])
        if isinstance(message, ModelRequest)
        else message
        for i, message in enumerate(messages)
    ]


def _context(part):
    if not isinstance(part, UserPromptPart) or not isinstance(part.content, str):
        return None
    marker = "\nCurrent target IDs: "
    if "\nApproved read-only intent:\n" not in part.content or marker not in part.content:
        return None
    return part.content.split(marker, 1)[0]

"""Trim superseded file reads without losing tool-result pairing or durable history."""

from dataclasses import replace
import json

from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart


def compact_authoring_history(messages):
    calls = {}
    newest = {}
    superseded = set()
    for message in messages:
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ToolCallPart) and part.tool_name == "read":
                    args = part.args_as_dict()
                    # Teaching reads are target-scoped; authoring reads are path/offset-scoped.
                    key = json.dumps(args, sort_keys=True)
                    calls[part.tool_call_id] = key
        elif isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, ToolReturnPart) and part.tool_call_id in calls:
                    key = calls[part.tool_call_id]
                    if key in newest:
                        superseded.add(newest[key])
                    newest[key] = part.tool_call_id
    return [
        replace(
            message,
            parts=[
                replace(part, content="Superseded by a newer read of the same file and offset.")
                if isinstance(part, ToolReturnPart) and part.tool_call_id in superseded
                else part
                for part in message.parts
            ],
        )
        if isinstance(message, ModelRequest)
        else message
        for message in messages
    ]

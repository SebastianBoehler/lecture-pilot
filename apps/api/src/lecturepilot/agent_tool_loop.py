from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.agent_response_schema import lecturepilot_response_format
from lecturepilot.agent_tool_schemas import AgentToolProfile, agent_tool_names, agent_tool_schemas
from lecturepilot.model_payload import agent_result_from_content
from lecturepilot.models import AgentTurnInput, AgentTurnResult, ProviderSettings
from lecturepilot.observability import Observability


async def complete_tool_turn(
    *,
    acompletion: Callable[..., Any],
    settings: ProviderSettings,
    turn: AgentTurnInput,
    tool_executor: AgentToolExecutor,
    observability: Observability,
    emit: Callable[[str], None] | None,
    messages: list[dict[str, str]],
    tool_profile: AgentToolProfile = "tutor",
) -> AgentTurnResult:
    messages = _with_tool_instruction(messages, tool_profile)
    enabled_tools = agent_tool_names(tool_profile)
    for _ in range(6):
        response = await acompletion(
            model=settings.model,
            messages=messages,
            tools=agent_tool_schemas(tool_profile),
            tool_choice="auto",
            temperature=0.3,
        )
        response_message = response.choices[0].message
        tool_calls = _tool_calls(response_message)
        if not tool_calls:
            content = _message_content(response_message)
            if content:
                return agent_result_from_content(content, turn, settings.model)
            return await _final_json_response(acompletion, settings, messages, turn)
        messages.append(_assistant_tool_message(response_message, tool_calls))
        for call in tool_calls[:6]:
            messages.append(_run_tool(call, tool_executor, observability, emit, enabled_tools))
    return await _final_json_response(acompletion, settings, messages, turn)


def _with_tool_instruction(messages: list[dict[str, str]], tool_profile: AgentToolProfile) -> list[dict[str, str]]:
    result = [dict(message) for message in messages]
    result[0]["content"] += (
        " You can use Pi-style low-level tools over a constrained filesystem image. "
        f"Active tool profile: {tool_profile}. "
        f"{_profile_instruction(tool_profile)} "
        "New learner canvas Markdown belongs under /lecture/canvas/student and is appended after "
        "the course canvas; do not claim it was inserted before the lecture content. "
        "When write creates canvas Markdown, use the returned path and section_id for focus/highlight. "
        "Do not duplicate a successful write/edit/generate_image as an append_section or update_section "
        "in the final JSON; the filesystem tool output is the source of truth. "
        "If the student asks for an infographic, diagram, image, plot, chart, graph, or visual, "
        "call generate_image before your final answer. Do not claim visual content was added unless "
        "generate_image returned ok=true. "
        "Use focus/highlight tools to navigate attention. "
        "After tool use, return only the final LecturePilot JSON."
    )
    return result


def _profile_instruction(tool_profile: AgentToolProfile) -> str:
    if tool_profile == "evidence":
        return "Use find/grep/read when you need exact course evidence; write/edit stay learner-owned only."
    if tool_profile == "course_builder":
        return "Use find/grep/read/write/edit/generate_image for course-authoring workspace tasks."
    return "Use read for known paths; write/edit stay learner-owned only. Search tools are disabled in this profile."


def _run_tool(
    call: Any,
    tool_executor: AgentToolExecutor,
    observability: Observability,
    emit: Callable[[str], None] | None,
    enabled_tools: set[str],
) -> dict[str, str]:
    name = _tool_name(call)
    args = _tool_args(call)
    if emit:
        emit(_tool_activity(name, args))
    with observability.tool_span(f"agent_tool_{name}", tool=name) as span:
        if name not in enabled_tools:
            result = {"ok": False, "error": f"Tool {name} is not enabled for this agent profile."}
        else:
            result = tool_executor.execute(name, args)
        span.set_outputs({"ok": result.get("ok"), "error": result.get("error")})
    return {
        "role": "tool",
        "tool_call_id": _tool_call_id(call),
        "name": name,
        "content": json.dumps(result, ensure_ascii=True),
    }


async def _final_json_response(
    acompletion: Callable[..., Any],
    settings: ProviderSettings,
    messages: list[dict[str, Any]],
    turn: AgentTurnInput,
) -> AgentTurnResult:
    response = await acompletion(
        model=settings.model,
        messages=[
            *messages,
            {
                "role": "user",
                "content": (
                    "Return the final LecturePilot JSON now. "
                    "Do not call another tool and do not leave the message empty."
                ),
            },
        ],
        temperature=0.3,
        response_format=lecturepilot_response_format(),
    )
    return agent_result_from_content(_message_content(response.choices[0].message), turn, settings.model)


def _tool_calls(message: Any) -> list[Any]:
    if isinstance(message, dict):
        return message.get("tool_calls") or []
    return getattr(message, "tool_calls", None) or []


def _message_content(message: Any) -> str | None:
    if isinstance(message, dict):
        return message.get("content")
    return getattr(message, "content", None)


def _assistant_tool_message(message: Any, tool_calls: list[Any]) -> dict[str, Any]:
    if isinstance(message, dict):
        return message
    calls = [call.model_dump() if hasattr(call, "model_dump") else _tool_call_dict(call) for call in tool_calls]
    return {"role": "assistant", "content": _message_content(message), "tool_calls": calls}


def _tool_call_dict(call: Any) -> dict[str, Any]:
    function = getattr(call, "function", None)
    return {
        "id": _tool_call_id(call),
        "type": getattr(call, "type", "function"),
        "function": {
            "name": getattr(function, "name", ""),
            "arguments": getattr(function, "arguments", "{}"),
        },
    }


def _tool_call_id(call: Any) -> str:
    if isinstance(call, dict):
        return str(call.get("id") or "")
    return str(getattr(call, "id", ""))


def _tool_name(call: Any) -> str:
    if isinstance(call, dict):
        function = call.get("function") or {}
        return str(function.get("name") or "")
    return str(getattr(getattr(call, "function", None), "name", ""))


def _tool_args(call: Any) -> dict[str, Any]:
    if isinstance(call, dict):
        raw = (call.get("function") or {}).get("arguments") or "{}"
    else:
        raw = getattr(getattr(call, "function", None), "arguments", "{}")
    if isinstance(raw, dict):
        return raw
    try:
        payload = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _tool_activity(name: str, args: dict[str, Any]) -> str:
    target = (
        args.get("path")
        or args.get("pattern")
        or args.get("section_id")
        or args.get("span_id")
        or args.get("gate_id")
        or ""
    )
    return f"{name}: {str(target)[:80]}" if target else name

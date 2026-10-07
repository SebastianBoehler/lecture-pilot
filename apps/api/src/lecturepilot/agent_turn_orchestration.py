from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

from fastapi import FastAPI, HTTPException
import anyio
from functools import partial
from datetime import UTC, datetime
from lecturepilot.model_usage_total import model_usage_total
from lecturepilot.agent_turn_context import load_turn_context

from lecturepilot.agent_state_access import (
    observability as app_observability,
)
from lecturepilot.agent_gate_persistence import persist_quality_gate
from lecturepilot.agent_command_utils import (
    enforce_active_gate_contract,
    merge_tool_outputs,
    without_generated_section_commands,
)
from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.coaching_orchestration import (
    persist_coaching_turn,
)
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.models import AgentTurnInput, AgentTurnResult
from lecturepilot.observability import Observability
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.usage_quota import UsageQuotaExceeded


async def complete_agent_turn(
    app: FastAPI,
    *,
    turn: AgentTurnInput,
    actor_user_id: str | None = None,
    emit: Callable[[str], None] | None = None,
) -> AgentTurnResult:
    actor_user_id = actor_user_id or turn.user_id
    reserved = False
    usage_date = datetime.now(UTC).date()
    try:
        reserved = await anyio.to_thread.run_sync(
            partial(
                app.state.usage_quota.reserve_turn,
                tenant_id=app.state.course_tenant_id,
                user_id=actor_user_id,
                course_id=turn.course_id,
                usage_date=usage_date,
            )
        )
    except (UsageQuotaExceeded, ValueError) as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    observability = app_observability(app)
    usage = model_usage_scope(
        actor_user_id=actor_user_id, course_id=turn.course_id, workload="tutor"
    )
    try:
        with usage, model_usage_total() as total, observability.agent_turn_span(turn) as span:
            result = await _complete_agent_turn_inner(
                app,
                turn=turn,
                emit=emit,
                observability=observability,
                actor_user_id=actor_user_id,
            )
            span.set_outputs(observability.result_output(result))
            return result
    finally:
        if reserved:
            await anyio.to_thread.run_sync(
                partial(
                    app.state.usage_quota.release_turn,
                    tenant_id=app.state.course_tenant_id,
                    user_id=actor_user_id,
                    course_id=turn.course_id,
                    usage_date=usage_date,
                    actual_tokens=total.total_tokens,
                )
            )


async def agent_turn_events(
    app: FastAPI,
    *,
    turn: AgentTurnInput,
    actor_user_id: str | None = None,
):
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def run_turn() -> None:
        try:
            result = await complete_agent_turn(
                app,
                turn=turn,
                actor_user_id=actor_user_id,
                emit=lambda tag: queue.put_nowait({"type": "activity", "tag": tag}),
            )
            await queue.put({"type": "result", "result": result.model_dump(mode="json")})
        except HTTPException as exc:
            await queue.put({"type": "error", "message": str(exc.detail)})
        finally:
            await queue.put(None)

    task = asyncio.create_task(run_turn())
    try:
        while True:
            event = await queue.get()
            if event is None:
                break
            yield f"{json.dumps(event)}\n"
    finally:
        await task


async def _complete_agent_turn_inner(
    app: FastAPI,
    *,
    turn: AgentTurnInput,
    emit: Callable[[str], None] | None,
    observability: Observability,
    actor_user_id: str,
) -> AgentTurnResult:
    loop = asyncio.get_running_loop()

    def activity(tag: str) -> None:
        if emit:
            loop.call_soon_threadsafe(emit, tag)

    turn, tool_executor = await anyio.to_thread.run_sync(
        load_turn_context, app, turn, activity, observability, actor_user_id
    )
    try:
        activity("call tutor model")
        with observability.model_span(course_id=turn.course_id, lecture_id=turn.lecture_id) as span:
            result = await _run_agent_harness(
                app.state.agent_harness,
                turn=turn,
                tool_executor=tool_executor,
                observability=observability,
                emit=activity,
            )
            span.set_outputs(observability.result_output(result))
    except ProviderConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ModelExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return await anyio.to_thread.run_sync(
        partial(
            _persist_agent_turn_result,
            app,
            turn=turn,
            result=result,
            tool_executor=tool_executor,
            activity=activity,
            observability=observability,
        )
    )


async def _run_agent_harness(
    harness,
    *,
    turn: AgentTurnInput,
    tool_executor: AgentToolExecutor | None,
    observability: Observability,
    emit: Callable[[str], None],
) -> AgentTurnResult:
    return await harness.run_turn(
        turn,
        tool_executor=tool_executor,
        observability=observability,
        emit=emit,
    )


def _persist_agent_turn_result(
    app: FastAPI,
    *,
    turn: AgentTurnInput,
    result: AgentTurnResult,
    tool_executor: AgentToolExecutor | None,
    activity: Callable[[str], None],
    observability: Observability,
) -> AgentTurnResult:
    if tool_executor is not None and tool_executor.canvas_changed:
        result = without_generated_section_commands(result)
    placements = {
        command.section.id: command.placement
        for command in result.canvas_commands
        if command.section and command.placement
    }
    sections = [command.section for command in result.canvas_commands if command.section]
    if sections:
        result = _apply_generated_sections(
            app,
            turn=turn,
            result=result,
            sections=sections,
            placements=placements,
            activity=activity,
            observability=observability,
        )
    if tool_executor is not None:
        result = merge_tool_outputs(result, tool_executor)
    result = enforce_active_gate_contract(result, turn)
    coaching_event = persist_coaching_turn(app, turn, result, activity, observability)
    persist_quality_gate(
        app,
        turn=turn,
        result=result,
        activity=activity,
        observability=observability,
        coaching_event=coaching_event,
    )
    return result


def _apply_generated_sections(app, *, turn, result, sections, placements, activity, observability):
    activity("write canvas update")
    with observability.tool_span(
        "write_canvas_update",
        section_count=len(sections),
        section_ids=",".join(section.id for section in sections[:8]),
    ):
        app.state.canvas_workspace.apply_sections(
            course_id=turn.course_id,
            lecture_id=turn.lecture_id,
            user_id=turn.user_id,
            sections=sections,
            placements=placements,
        )
    return result

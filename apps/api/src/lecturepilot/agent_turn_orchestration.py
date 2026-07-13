from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

from fastapi import FastAPI, HTTPException

from lecturepilot.agent_state_access import (
    analytics_store as app_analytics_store,
    learner_state_store,
    observability as app_observability,
    user_memory_store,
)
from lecturepilot.agent_command_utils import dedupe_commands
from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.coaching_orchestration import persist_coaching_turn, prepare_coaching_turn
from lecturepilot.gate_policy import keep_canvas_actions_from_passing_gate
from lecturepilot.image_generation import ImageGenerationError
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
    emit: Callable[[str], None] | None = None,
) -> AgentTurnResult:
    reserved = False
    try:
        reserved = app.state.usage_quota.reserve_turn(
            tenant_id=app.state.course_tenant_id,
            user_id=turn.user_id,
            course_id=turn.course_id,
        )
    except (UsageQuotaExceeded, ValueError) as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    observability = app_observability(app)
    usage = model_usage_scope(actor_user_id=turn.user_id, course_id=turn.course_id, workload="tutor")
    try:
        with usage, observability.agent_turn_span(turn) as span:
            result = await _complete_agent_turn_inner(
                app,
                turn=turn,
                emit=emit,
                observability=observability,
            )
            span.set_outputs(observability.result_output(result))
            return result
    finally:
        if reserved:
            app.state.usage_quota.release_turn(
                tenant_id=app.state.course_tenant_id,
                user_id=turn.user_id,
                course_id=turn.course_id,
            )


async def agent_turn_events(app: FastAPI, *, turn: AgentTurnInput):
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def run_turn() -> None:
        try:
            result = await complete_agent_turn(
                app,
                turn=turn,
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
) -> AgentTurnResult:
    def activity(tag: str) -> None:
        if emit:
            emit(tag)

    tool_executor = None
    if turn.course_id:
        activity("read canvas")
        try:
            activity("load learner memory")
            with observability.tool_span(
                "read_canvas", course_id=turn.course_id, lecture_id=turn.lecture_id
            ):
                document = app.state.canvas_workspace.read_document(
                    course_id=turn.course_id,
                    lecture_id=turn.lecture_id,
                    user_id=turn.user_id,
                )
            with observability.tool_span("read_user_memory"):
                memory = user_memory_store(app).read_context(turn.user_id, turn.course_id)
            activity("save attendance")
            with observability.tool_span("write_attendance", attendance=turn.attendance.value):
                learner_state_store(app).write_attendance(
                    course_id=turn.course_id,
                    lecture_id=turn.lecture_id,
                    user_id=turn.user_id,
                    attendance=turn.attendance,
                )
            turn = turn.model_copy(update={"canvas_context": document, "user_memory": memory})
            layout = getattr(app.state.canvas_workspace, "layout", None)
            if callable(getattr(layout, "user_canvas_dir", None)):
                tool_executor = AgentToolExecutor(
                    canvas_workspace=app.state.canvas_workspace,
                    course_id=turn.course_id,
                    lecture_id=turn.lecture_id,
                    user_id=turn.user_id,
                    image_generator=getattr(app.state, "image_generator", None),
                    usage_quota=app.state.usage_quota,
                    tenant_id=app.state.course_tenant_id,
                    user_message=turn.message,
                )
        except CanvasWorkspaceError:
            pass
    turn = prepare_coaching_turn(app, turn, activity, observability)
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

    return _persist_agent_turn_result(
        app,
        turn=turn,
        result=result,
        tool_executor=tool_executor,
        activity=activity,
        observability=observability,
    )


async def _run_agent_harness(
    harness,
    *,
    turn: AgentTurnInput,
    tool_executor: AgentToolExecutor | None,
    observability: Observability,
    emit: Callable[[str], None],
) -> AgentTurnResult:
    try:
        return await harness.run_turn(
            turn,
            tool_executor=tool_executor,
            observability=observability,
            emit=emit,
        )
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        return await harness.run_turn(turn)


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
        result = _without_generated_section_commands(result)
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
        result = _merge_tool_outputs(result, tool_executor)
    result = keep_canvas_actions_from_passing_gate(result, turn.message)
    if result.quality_gate is not None and turn.course_id:
        activity("save quality gate")
        with observability.tool_span(
            "record_quality_gate",
            gate_id=result.quality_gate.gate_id,
            status=result.quality_gate.status.value,
        ):
            learner_state_store(app).record_quality_gate(
                course_id=turn.course_id,
                lecture_id=turn.lecture_id,
                user_id=turn.user_id,
                decision=result.quality_gate,
            )
            analytics_store = app_analytics_store(app)
            if analytics_store is not None:
                analytics_store.record_quality_gate(
                    course_id=turn.course_id,
                    lecture_id=turn.lecture_id,
                    user_id=turn.user_id,
                    attendance=turn.attendance,
                    decision=result.quality_gate,
                )
    persist_coaching_turn(app, turn, result, activity, observability)
    return result


def _apply_generated_sections(app, *, turn, result, sections, placements, activity, observability):
    try:
        activity("prepare canvas update")
        with observability.tool_span("prepare_canvas_update", section_count=len(sections)):
            sections = app.state.canvas_workspace.prepare_generated_sections(
                course_id=turn.course_id,
                lecture_id=turn.lecture_id,
                user_id=turn.user_id,
                prompt=turn.message,
                sections=sections,
            )
    except ImageGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    result = _replace_generated_sections(result, sections)
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


def _replace_generated_sections(result: AgentTurnResult, sections) -> AgentTurnResult:
    sections_by_id = {section.id: section for section in sections}
    commands = [
        command.model_copy(update={"section": sections_by_id[command.section.id]})
        if command.section and command.section.id in sections_by_id
        else command
        for command in result.canvas_commands
    ]
    return result.model_copy(update={"canvas_commands": commands})


def _without_generated_section_commands(result: AgentTurnResult) -> AgentTurnResult:
    commands = [
        command
        for command in result.canvas_commands
        if command.type not in {"append_section", "update_section"}
    ]
    return result.model_copy(update={"canvas_commands": commands})


def _merge_tool_outputs(
    result: AgentTurnResult, tool_executor: AgentToolExecutor
) -> AgentTurnResult:
    commands = dedupe_commands([*result.canvas_commands, *tool_executor.canvas_update_commands()])
    gate = tool_executor.gate or result.quality_gate
    return result.model_copy(update={"canvas_commands": commands, "quality_gate": gate})

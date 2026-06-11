from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.gate_policy import keep_canvas_actions_from_passing_gate
from lecturepilot.image_generation import ImageGenerationError
from lecturepilot.learner_state import LearnerStateStore
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import AgentTurnInput, AgentTurnResult, CanvasCommand, Course
from lecturepilot.observability import Observability
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.user_memory import UserMemoryStore


def register_agent_routes(app: FastAPI, *, course: Course) -> None:
    @app.post("/agent/turn", response_model=AgentTurnResult)
    async def agent_turn(turn: AgentTurnInput) -> AgentTurnResult:
        return await _complete_agent_turn(app, course=course, turn=turn)

    @app.post("/agent/turn/stream")
    async def agent_turn_stream(turn: AgentTurnInput) -> StreamingResponse:
        return StreamingResponse(
            _agent_turn_events(app, course=course, turn=turn),
            media_type="application/x-ndjson",
        )


async def _complete_agent_turn(
    app: FastAPI,
    *,
    course: Course,
    turn: AgentTurnInput,
    emit: Callable[[str], None] | None = None,
) -> AgentTurnResult:
    observability = _observability(app)
    with observability.agent_turn_span(turn) as span:
        result = await _complete_agent_turn_inner(
            app,
            course=course,
            turn=turn,
            emit=emit,
            observability=observability,
        )
        span.set_outputs(observability.result_output(result))
        return result


async def _complete_agent_turn_inner(
    app: FastAPI,
    *,
    course: Course,
    turn: AgentTurnInput,
    emit: Callable[[str], None] | None,
    observability: Observability,
) -> AgentTurnResult:
    def activity(tag: str) -> None:
        if emit:
            emit(tag)

    tool_executor = None
    if turn.course_id == course.id:
        activity("read canvas")
        try:
            activity("load learner memory")
            with observability.tool_span(
                "read_canvas",
                course_id=turn.course_id,
                lecture_id=turn.lecture_id,
            ):
                document = app.state.canvas_workspace.read_document(
                    course_id=turn.course_id,
                    lecture_id=turn.lecture_id,
                    user_id=turn.user_id,
                )
            with observability.tool_span("read_user_memory"):
                memory = _user_memory_store(app).read_context(turn.user_id)
            activity("save attendance")
            with observability.tool_span("write_attendance", attendance=turn.attendance.value):
                _learner_state_store(app).write_attendance(
                    course_id=turn.course_id,
                    lecture_id=turn.lecture_id,
                    user_id=turn.user_id,
                    attendance=turn.attendance,
                )
            turn = turn.model_copy(update={"canvas_context": document, "user_memory": memory})
            tool_executor = AgentToolExecutor(
                canvas_workspace=app.state.canvas_workspace,
                course_id=turn.course_id,
                lecture_id=turn.lecture_id,
                user_id=turn.user_id,
                image_generator=getattr(app.state, "image_generator", None),
            )
        except CanvasWorkspaceError:
            pass
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

    if tool_executor is not None and tool_executor.canvas_changed:
        result = _without_generated_section_commands(result)
    sections = [command.section for command in result.canvas_commands if command.section]
    if sections:
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
            )
    if tool_executor is not None:
        result = _merge_tool_outputs(result, tool_executor)
    result = keep_canvas_actions_from_passing_gate(result, turn.message)
    if result.quality_gate is not None and turn.course_id == course.id:
        activity("save quality gate")
        with observability.tool_span(
            "record_quality_gate",
            gate_id=result.quality_gate.gate_id,
            status=result.quality_gate.status.value,
        ):
            _learner_state_store(app).record_quality_gate(
                course_id=turn.course_id,
                lecture_id=turn.lecture_id,
                user_id=turn.user_id,
                decision=result.quality_gate,
            )
    return result


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


async def _agent_turn_events(app: FastAPI, *, course: Course, turn: AgentTurnInput):
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def run_turn() -> None:
        try:
            result = await _complete_agent_turn(
                app,
                course=course,
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


def _replace_generated_sections(
    result: AgentTurnResult,
    sections,
) -> AgentTurnResult:
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
    result: AgentTurnResult,
    tool_executor: AgentToolExecutor,
) -> AgentTurnResult:
    commands = _dedupe_commands([*result.canvas_commands, *tool_executor.canvas_update_commands()])
    gate = tool_executor.gate or result.quality_gate
    return result.model_copy(update={"canvas_commands": commands, "quality_gate": gate})


def _dedupe_commands(commands: list[CanvasCommand]) -> list[CanvasCommand]:
    result: list[CanvasCommand] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    for command in commands:
        key = (command.type, command.section_id, command.span_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(command)
    return result


def _user_memory_store(app: FastAPI) -> UserMemoryStore:
    store = app.state.user_memory_store
    layout = getattr(app.state.canvas_workspace, "layout", None)
    if layout is not None and store.layout is not layout:
        store = UserMemoryStore(layout)
        app.state.user_memory_store = store
    return store


def _learner_state_store(app: FastAPI) -> LearnerStateStore:
    store = app.state.learner_state
    layout = getattr(app.state.canvas_workspace, "layout", None)
    if layout is not None and store.layout is not layout:
        store = LearnerStateStore(layout)
        app.state.learner_state = store
    return store


def _observability(app: FastAPI) -> Observability:
    return getattr(app.state, "observability", Observability())

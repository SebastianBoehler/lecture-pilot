from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.image_generation import ImageGenerationError
from lecturepilot.learner_state import LearnerStateStore
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import AgentTurnInput, AgentTurnResult, Course
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
    def activity(tag: str) -> None:
        if emit:
            emit(tag)

    if turn.course_id == course.id:
        activity("read canvas")
        try:
            activity("load learner memory")
            document = app.state.canvas_workspace.read_document(
                course_id=turn.course_id,
                lecture_id=turn.lecture_id,
                user_id=turn.user_id,
            )
            memory = _user_memory_store(app).read_context(turn.user_id)
            activity("save attendance")
            _learner_state_store(app).write_attendance(
                course_id=turn.course_id,
                lecture_id=turn.lecture_id,
                user_id=turn.user_id,
                attendance=turn.attendance,
            )
            turn = turn.model_copy(update={"canvas_context": document, "user_memory": memory})
        except CanvasWorkspaceError:
            pass
    try:
        activity("call tutor model")
        result = await app.state.agent_harness.run_turn(turn)
    except ProviderConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ModelExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    sections = [command.section for command in result.canvas_commands if command.section]
    if sections:
        try:
            activity("prepare canvas update")
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
        app.state.canvas_workspace.apply_sections(
            course_id=turn.course_id,
            lecture_id=turn.lecture_id,
            user_id=turn.user_id,
            sections=sections,
        )
    if result.quality_gate is not None and turn.course_id == course.id:
        activity("save quality gate")
        _learner_state_store(app).record_quality_gate(
            course_id=turn.course_id,
            lecture_id=turn.lecture_id,
            user_id=turn.user_id,
            decision=result.quality_gate,
        )
    return result


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

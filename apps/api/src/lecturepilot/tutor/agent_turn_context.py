from collections.abc import Callable
from fastapi import FastAPI, HTTPException
from lecturepilot.tutor.agent_state_access import learner_state_store, user_memory_store
from lecturepilot.tutor.agent_tool_executor import AgentToolExecutor
from lecturepilot.learner.assessment_history import load_assessment_history
from lecturepilot.canvas.canvas_predictions import prediction_context
from lecturepilot.canvas.canvas_workspace import CanvasWorkspaceError
from lecturepilot.canvas.course_canvas_context import (
    AnalyticsPublicationContext,
    InvalidPublishedCanvasContextError,
)
from lecturepilot.learner.coaching_progress import CoachingProgressStore
from lecturepilot.learner.independent_attempt import reject_chat_during_independent_attempt
from lecturepilot.learner.coaching_orchestration import prepare_coaching_turn
from lecturepilot.core.models import AgentTurnInput
from lecturepilot.core.observability import Observability


def load_turn_context(
    app: FastAPI,
    turn: AgentTurnInput,
    activity: Callable[[str], None],
    observability: Observability,
    actor_user_id: str,
):
    if turn.recall_publication_version:
        activity("read canvas")
        return _load_recall_context(app, turn), None
    tool_executor = None
    analytics_context = None
    if turn.course_id:
        activity("read canvas")
        try:
            activity("load learner memory")
            with observability.tool_span(
                "read_canvas", course_id=turn.course_id, lecture_id=turn.lecture_id
            ):
                snapshot = app.state.canvas_workspace.read_published_canvas_view(
                    course_id=turn.course_id,
                    lecture_id=turn.lecture_id,
                    user_id=turn.user_id,
                )
                if snapshot is None:
                    raise InvalidPublishedCanvasContextError("Canvas has not been published.")
                document = snapshot.document
                overlay = app.state.canvas_workspace.read_learner_overlay_sections(
                    course_id=turn.course_id, lecture_id=turn.lecture_id, user_id=turn.user_id
                )
                analytics_context = AnalyticsPublicationContext(
                    snapshot.learning_map, snapshot.version, snapshot.learning_map_revision
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
            turn = turn.model_copy(
                update={
                    "canvas_context": document,
                    "learner_section_ids": [section.id for section in overlay],
                    "user_memory": memory,
                }
            )
            layout = getattr(app.state.canvas_workspace, "layout", None)
            if callable(getattr(layout, "user_canvas_dir", None)):
                turn = turn.model_copy(
                    update={
                        "predictions": prediction_context(
                            app.state.canvas_workspace, turn, snapshot=snapshot
                        )
                    }
                )
                activity("read assessment history")
                history = load_assessment_history(
                    layout,
                    user_id=turn.user_id,
                    course_id=turn.course_id,
                    lecture_id=turn.lecture_id,
                )
                turn = turn.model_copy(update={"assessment_history": history})
                tool_executor = AgentToolExecutor(
                    canvas_workspace=app.state.canvas_workspace,
                    course_id=turn.course_id,
                    lecture_id=turn.lecture_id,
                    user_id=turn.user_id,
                    quota_user_id=actor_user_id,
                    image_generator=getattr(app.state, "image_generator", None),
                    usage_quota=app.state.usage_quota,
                    tenant_id=app.state.course_tenant_id,
                    user_message=turn.message,
                    initial_focus_section_id=turn.canvas_state.focused_section_id,
                )
        except CanvasWorkspaceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    turn = prepare_coaching_turn(
        app, turn, activity, observability, analytics_context=analytics_context
    )
    return turn, tool_executor


def _load_recall_context(app: FastAPI, turn: AgentTurnInput) -> AgentTurnInput:
    workspace = app.state.canvas_workspace
    snapshot = workspace.course_canvas_store.read_current_published_snapshot(
        course_id=turn.course_id, lecture_id=turn.lecture_id
    )
    if snapshot is None or snapshot.version != turn.recall_publication_version:
        raise HTTPException(409, "The recall section is no longer published.")
    section = next(
        (
            item
            for item in snapshot.document.sections
            if item.id == turn.canvas_state.focused_section_id
        ),
        None,
    )
    if section is None:
        raise HTTPException(409, "The recall section is no longer published.")
    pending = (
        CoachingProgressStore(workspace.layout)
        .read(user_id=turn.user_id, course_id=turn.course_id, lecture_id=turn.lecture_id)
        .pending_check
    )
    reject_chat_during_independent_attempt(
        checkpoint_gate_id=None, stage=pending.stage if pending else None
    )
    document = snapshot.document.model_copy(update={"sections": [section]})
    return turn.model_copy(update={"canvas_context": document})

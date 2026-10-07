from collections.abc import Callable
from fastapi import FastAPI, HTTPException
from lecturepilot.agent_state_access import learner_state_store, user_memory_store
from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.assessment_history import load_assessment_history
from lecturepilot.canvas_predictions import prediction_context
from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.course_canvas_context import (
    AnalyticsPublicationContext,
    InvalidPublishedCanvasContextError,
)
from lecturepilot.coaching_orchestration import prepare_coaching_turn
from lecturepilot.models import AgentTurnInput
from lecturepilot.observability import Observability


def load_turn_context(
    app: FastAPI,
    turn: AgentTurnInput,
    activity: Callable[[str], None],
    observability: Observability,
    actor_user_id: str,
):
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
            turn = turn.model_copy(update={"canvas_context": document, "user_memory": memory})
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

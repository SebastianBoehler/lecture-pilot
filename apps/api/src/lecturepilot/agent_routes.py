from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.responses import StreamingResponse

from lecturepilot.agent_authorization import authorize_agent_turn
from lecturepilot.agent_turn_orchestration import agent_turn_events, complete_agent_turn
from lecturepilot.api_auth import request_context
from lecturepilot.models import AgentTurnRequest, AgentTurnResult, Course, Lecture
from lecturepilot.professor_preview import resolve_learner_workspace_access
from lecturepilot.tenancy import TenantContext


def register_agent_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> None:
    @app.post("/agent/turn", response_model=AgentTurnResult)
    async def agent_turn(
        input_data: AgentTurnRequest,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> AgentTurnResult:
        access = resolve_learner_workspace_access(
            request,
            context,
            course_id=input_data.course_id,
            course_tenant_id=course_tenant_id,
        )
        turn = input_data.for_user(access.user_id)
        authorize_agent_turn(
            app,
            context,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
            turn=turn,
        )
        return await complete_agent_turn(app, turn=turn, actor_user_id=access.actor_user_id)

    @app.post("/agent/turn/stream")
    async def agent_turn_stream(
        input_data: AgentTurnRequest,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> StreamingResponse:
        access = resolve_learner_workspace_access(
            request,
            context,
            course_id=input_data.course_id,
            course_tenant_id=course_tenant_id,
        )
        turn = input_data.for_user(access.user_id)
        authorize_agent_turn(
            app,
            context,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
            turn=turn,
        )
        return StreamingResponse(
            agent_turn_events(app, turn=turn, actor_user_id=access.actor_user_id),
            media_type="application/x-ndjson",
        )

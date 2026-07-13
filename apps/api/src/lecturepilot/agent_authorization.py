from __future__ import annotations

from fastapi import FastAPI

from lecturepilot.course_access import require_lecture_id_access
from lecturepilot.models import AgentTurnInput, Course, Lecture
from lecturepilot.tenancy import TenantContext


def authorize_agent_turn(
    app: FastAPI,
    context: TenantContext,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
    turn: AgentTurnInput,
) -> None:
    require_lecture_id_access(
        app,
        context,
        course_id=turn.course_id,
        lecture_id=turn.lecture_id,
        course_tenant_id=course_tenant_id,
        seeded_course=seeded_course,
        seeded_lectures=seeded_lectures,
    )

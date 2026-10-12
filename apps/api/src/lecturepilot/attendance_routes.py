"""Learners mark lecture attendance; the tutor adapts and the choice survives reloads."""

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel

from lecturepilot.agent_state_access import learner_state_store
from lecturepilot.course_access import require_lecture_id_access
from lecturepilot.models import AttendanceStatus, Course, Lecture
from lecturepilot.professor_preview import resolve_learner_workspace_access
from lecturepilot.api_auth import request_context
from lecturepilot.tenancy import TenantContext


class AttendanceInput(BaseModel):
    attendance: AttendanceStatus


class AttendanceResult(BaseModel):
    lecture_id: str
    attendance: AttendanceStatus


def register_attendance_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> None:
    @app.put(
        "/courses/{course_id}/lectures/{lecture_id}/attendance",
        response_model=AttendanceResult,
    )
    def set_attendance(
        course_id: str,
        lecture_id: str,
        payload: AttendanceInput,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> AttendanceResult:
        access = resolve_learner_workspace_access(
            request, context, course_id=course_id, course_tenant_id=course_tenant_id
        )
        require_lecture_id_access(
            app,
            context,
            course_id=course_id,
            lecture_id=lecture_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
        )
        learner_state_store(app).write_attendance(
            course_id=course_id,
            lecture_id=lecture_id,
            user_id=access.user_id,
            attendance=payload.attendance,
        )
        return AttendanceResult(lecture_id=lecture_id, attendance=payload.attendance)

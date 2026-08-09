from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.agent_state_access import learner_state_store
from lecturepilot.api_auth import request_context
from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.course_access import require_lecture_id_access
from lecturepilot.learner_lesson_state import lesson_state_snapshot
from lecturepilot.learner_lesson_state_models import LearnerLessonState
from lecturepilot.models import Course, Lecture
from lecturepilot.professor_preview import resolve_learner_workspace_access
from lecturepilot.quiz_identity import published_canvas_version
from lecturepilot.tenancy import TenantContext


def register_learner_lesson_state_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> None:
    @app.get(
        "/courses/{course_id}/lectures/{lecture_id}/learner-state",
        response_model=LearnerLessonState,
    )
    def learner_lesson_state(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> LearnerLessonState:
        access = resolve_learner_workspace_access(
            request,
            context,
            course_id=course_id,
            course_tenant_id=course_tenant_id,
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
        if not app.state.canvas_workspace.has_published_course_canvas(
            course_id=course_id,
            lecture_id=lecture_id,
        ):
            raise HTTPException(status_code=404, detail="Canvas has not been published.")
        layout = app.state.canvas_workspace.layout
        return lesson_state_snapshot(
            learner_store=learner_state_store(app),
            coaching_store=CoachingProgressStore(layout),
            user_id=access.user_id,
            course_id=course_id,
            lecture_id=lecture_id,
            publication_version=published_canvas_version(
                app.state.canvas_workspace,
                course_id=course_id,
                lecture_id=lecture_id,
            ),
        )

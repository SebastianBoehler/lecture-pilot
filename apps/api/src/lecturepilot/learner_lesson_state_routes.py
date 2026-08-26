from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.agent_state_access import learner_state_store
from lecturepilot.api_auth import request_context
from lecturepilot.audit import record_audit_event
from lecturepilot.coaching_progress import CoachingProgressStore, InvalidCoachingStateError
from lecturepilot.coaching_state_recovery import (
    CoachingStateRecoveryNotRequired,
    CoachingStateRecoveryResult,
    recover_invalid_coaching_state,
    recovery_required_detail,
)
from lecturepilot.course_access import require_lecture_id_access
from lecturepilot.learner_lesson_state import lesson_state_snapshot
from lecturepilot.learner_lesson_state_models import LearnerLessonState
from lecturepilot.models import Course, Lecture
from lecturepilot.learning_state_preflight import validate_coaching_bindings
from lecturepilot.professor_preview import resolve_learner_workspace_access
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
        snapshot = app.state.canvas_workspace.course_canvas_store.read_current_published_snapshot(
            course_id=course_id,
            lecture_id=lecture_id,
        )
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Canvas has not been published.")
        layout = app.state.canvas_workspace.layout
        coaching_store = CoachingProgressStore(layout)
        try:
            progress = coaching_store.read(
                user_id=access.user_id,
                course_id=course_id,
                lecture_id=lecture_id,
            )
            validate_coaching_bindings(progress, snapshot.learning_map)
        except InvalidCoachingStateError as exc:
            raise HTTPException(
                status_code=409,
                detail=recovery_required_detail(course_id, lecture_id),
            ) from exc
        return lesson_state_snapshot(
            learner_store=learner_state_store(app),
            coaching_store=coaching_store,
            user_id=access.user_id,
            course_id=course_id,
            lecture_id=lecture_id,
            publication_version=snapshot.version,
            progress=progress,
        )

    @app.post(
        "/courses/{course_id}/lectures/{lecture_id}/learner-state/recover",
        response_model=CoachingStateRecoveryResult,
    )
    def recover_learner_coaching_state(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CoachingStateRecoveryResult:
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
        canvas_store = app.state.canvas_workspace.course_canvas_store
        with canvas_store.locked_published_learning_map(
            course_id=course_id,
            lecture_id=lecture_id,
        ) as learning_map:
            if learning_map is None:
                raise HTTPException(status_code=404, detail="Canvas has not been published.")
            try:
                result = recover_invalid_coaching_state(
                    layout=app.state.canvas_workspace.layout,
                    learner_store=learner_state_store(app),
                    learning_map=learning_map,
                    user_id=access.user_id,
                    course_id=course_id,
                    lecture_id=lecture_id,
                )
            except CoachingStateRecoveryNotRequired as exc:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "coaching_state_recovery_not_required",
                        "message": ("Persisted coaching state is valid; recovery was not applied."),
                    },
                ) from exc
            record_audit_event(
                app.state.database,
                context,
                event_type="learner.coaching_state_recovered",
                target_type="lecture",
                target_id=lecture_id,
                details={
                    "course_id": course_id,
                    "cleared_gate_ids": result.cleared_gate_ids,
                },
            )
            return result

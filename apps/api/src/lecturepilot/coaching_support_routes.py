from fastapi import Depends, HTTPException, Request

from lecturepilot.agent_state_access import learner_state_store
from lecturepilot.api_auth import request_context
from lecturepilot.coaching_progress import CoachingProgressStore, InvalidCoachingStateError
from lecturepilot.coaching_support import CoachingSupportRequest, request_support
from lecturepilot.course_canvas_context import read_published_snapshot_locked
from lecturepilot.course_access import require_lecture_id_access
from lecturepilot.learner_lesson_state import lesson_state_snapshot
from lecturepilot.learner_lesson_state_models import LearnerLessonState
from lecturepilot.learning_state_preflight import validate_coaching_bindings
from lecturepilot.professor_preview import resolve_learner_workspace_access
from lecturepilot.tenancy import TenantContext


def register_coaching_support_routes(app, *, course_tenant_id, seeded_course, seeded_lectures):
    @app.post(
        "/courses/{course_id}/lectures/{lecture_id}/learner-state/support",
        response_model=LearnerLessonState,
    )
    def support(
        course_id: str,
        lecture_id: str,
        payload: CoachingSupportRequest,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
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
                raise HTTPException(404, "Canvas has not been published.")
            gate = next((g for g in learning_map.gates if g.id == payload.gate_id), None)
            if gate is None or gate.revision != payload.gate_revision:
                raise HTTPException(
                    409, "The published task changed; reload before requesting help."
                )
            ids = dict(user_id=access.user_id, course_id=course_id, lecture_id=lecture_id)
            store = CoachingProgressStore(app.state.canvas_workspace.layout)
            try:
                validate_coaching_bindings(store.read(**ids), learning_map)
                progress = request_support(store, **ids, gate=gate, request=payload)
            except (InvalidCoachingStateError, ValueError) as exc:
                raise HTTPException(409, str(exc)) from exc
            snapshot = read_published_snapshot_locked(
                canvas_store.path(course_id, lecture_id),
                course_id=course_id,
                lecture_id=lecture_id,
            )
            return lesson_state_snapshot(
                learner_store=learner_state_store(app),
                coaching_store=store,
                **ids,
                publication_version=snapshot.version,
                learning_map=snapshot.learning_map,
                progress=progress,
            )

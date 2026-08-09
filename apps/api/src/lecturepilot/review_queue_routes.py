from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.api_auth import request_context
from lecturepilot.coaching_check_binding import bind_delayed_review
from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.course_access import (
    lecture_views_for_context,
    require_course_id_access,
    require_lecture_id_access,
    resolve_course_lectures,
)
from lecturepilot.models import Course, Lecture
from lecturepilot.professor_preview import (
    is_professor_preview_user_id,
    resolve_learner_workspace_access,
)
from lecturepilot.review_queue import ReviewQueueLecture, ReviewQueueStore
from lecturepilot.review_queue_models import CourseReviewQueue, GateReviewOpening
from lecturepilot.tenancy import TenantContext


def register_review_queue_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> None:
    @app.get("/courses/{course_id}/review-queue", response_model=CourseReviewQueue)
    def review_queue(
        course_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CourseReviewQueue:
        user_id = _learner_user_id(request, context, course_id, course_tenant_id)
        course, lectures = resolve_course_lectures(
            app,
            course_id=course_id,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
        )
        require_course_id_access(
            app,
            context,
            course_id=course_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
        )
        accessible = []
        for view in lecture_views_for_context(
            app,
            context,
            course,
            lectures,
            course_tenant_id=course_tenant_id,
        ):
            if not view.unlocked or not view.content_ready:
                continue
            learning_map = app.state.canvas_workspace.course_canvas_store.learning_map(
                course_id=course_id,
                lecture_id=view.lecture.id,
            )
            if learning_map is not None:
                accessible.append(
                    ReviewQueueLecture(
                        id=view.lecture.id,
                        title=view.lecture.title,
                        learning_map=learning_map,
                    )
                )
        return ReviewQueueStore(app.state.canvas_workspace.layout).read_course(
            user_id=user_id,
            course_id=course_id,
            lectures=accessible,
        )

    @app.post(
        "/courses/{course_id}/review-queue/gates/{lecture_id}/{gate_id}/open",
        response_model=GateReviewOpening,
    )
    def open_gate_review(
        course_id: str,
        lecture_id: str,
        gate_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> GateReviewOpening:
        user_id = _learner_user_id(request, context, course_id, course_tenant_id)
        _, lecture = require_lecture_id_access(
            app,
            context,
            course_id=course_id,
            lecture_id=lecture_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
        )
        learning_map = app.state.canvas_workspace.course_canvas_store.learning_map(
            course_id=course_id,
            lecture_id=lecture.id,
        )
        gate = (
            next(
                (item for item in learning_map.gates if item.id == gate_id),
                None,
            )
            if learning_map is not None
            else None
        )
        if gate is None:
            raise HTTPException(status_code=404, detail="Gate review is not available.")
        if not gate.transfer_prompt:
            raise HTTPException(status_code=409, detail="Gate has no delayed transfer prompt.")
        store = CoachingProgressStore(app.state.canvas_workspace.layout)
        try:
            pending = bind_delayed_review(
                store,
                user_id=user_id,
                course_id=course_id,
                lecture_id=lecture.id,
                gate_id=gate.id,
                gate_revision=gate.revision,
                transfer_prompt=gate.transfer_prompt,
                now=datetime.now(UTC),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return GateReviewOpening(
            course_id=course_id,
            lecture_id=lecture.id,
            section_id=gate.section_id,
            gate_id=gate.id,
            gate_revision=gate.revision,
            prompt=pending.prompt,
            stage="due" if pending.kind == "delayed_transfer" else "repair",
        )


def _learner_user_id(
    request: Request,
    context: TenantContext,
    course_id: str,
    course_tenant_id: str,
) -> str:
    access = resolve_learner_workspace_access(
        request,
        context,
        course_id=course_id,
        course_tenant_id=course_tenant_id,
    )
    if is_professor_preview_user_id(access.user_id):
        raise HTTPException(status_code=403, detail="Review queue is available to learners only.")
    return access.user_id

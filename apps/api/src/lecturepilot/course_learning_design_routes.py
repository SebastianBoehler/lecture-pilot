from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.api_auth import request_context, require_course_manager
from lecturepilot.course_learning_design_models import (
    LearningDesignApprovalInput,
    LearningDesignReview,
    LearningDesignUpdate,
)
from lecturepilot.course_learning_design_store import (
    CourseLearningDesignStore,
    LearningDesignError,
    LearningDesignStaleError,
    LearningDesignUnavailableError,
)
from lecturepilot.tenancy import TenantContext


def register_course_learning_design_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
) -> None:
    @app.get(
        "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/learning-design",
        response_model=LearningDesignReview,
    )
    def learning_design_review(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> LearningDesignReview:
        _require_owner(request, context, course_id, course_tenant_id)
        return _run(lambda: _store(app).read(course_id=course_id, lecture_id=lecture_id))

    @app.put(
        "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/learning-design",
        response_model=LearningDesignReview,
    )
    def update_learning_design(
        course_id: str,
        lecture_id: str,
        update: LearningDesignUpdate,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> LearningDesignReview:
        _require_owner(request, context, course_id, course_tenant_id)
        return _run(
            lambda: _store(app).update(
                course_id=course_id,
                lecture_id=lecture_id,
                update=update,
            )
        )

    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/learning-design/approve",
        response_model=LearningDesignReview,
    )
    def approve_learning_design(
        course_id: str,
        lecture_id: str,
        approval: LearningDesignApprovalInput,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> LearningDesignReview:
        _require_owner(request, context, course_id, course_tenant_id)
        return _run(
            lambda: _store(app).approve(
                course_id=course_id,
                lecture_id=lecture_id,
                draft_digest=approval.draft_digest,
                source_revision=approval.source_revision,
                approved_by=context.user_id,
            )
        )


def _store(app: FastAPI) -> CourseLearningDesignStore:
    return CourseLearningDesignStore(app.state.canvas_workspace.layout)


def _run(operation):
    try:
        return operation()
    except LearningDesignUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LearningDesignStaleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LearningDesignError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _require_owner(
    request: Request,
    context: TenantContext,
    course_id: str,
    tenant_id: str,
) -> None:
    require_course_manager(
        context,
        course_tenant_id=tenant_id,
        request=request,
        course_id=course_id,
    )

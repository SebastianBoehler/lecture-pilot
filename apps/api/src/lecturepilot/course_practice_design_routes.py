from __future__ import annotations

from lecturepilot.course_practice_design_route_context import (
    _require_manager,
    _source_context,
    _source_revision,
)

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.api_auth import request_context
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_learning_intent_routes import register_learning_intent_routes
from lecturepilot.course_practice_design_models import (
    PracticeDesign,
    PracticeDesignApprovalInput,
    PracticeDesignUpdate,
)
from lecturepilot.course_practice_design_proposal_routes import (
    register_practice_design_proposal_route,
)
from lecturepilot.course_practice_design_readiness import PracticeDesignReadiness
from lecturepilot.course_practice_design_review_routes import (
    register_practice_design_review_route,
)
from lecturepilot.course_practice_design_store import (
    PracticeDesignApprovalRequired,
    PracticeDesignStale,
    PracticeDesignStore,
    PracticeDesignUnavailable,
)
from lecturepilot.course_practice_design_validation import PracticeDesignValidationError
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.tenancy import TenantContext


def register_course_practice_design_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    source_document: Callable[[str, str], CanvasDocument],
) -> None:
    @app.get(
        "/admin/courses/{course_id}/lectures/{lecture_id}/practice-design",
        response_model=PracticeDesign,
    )
    def get_practice_design(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> PracticeDesign:
        _require_manager(context, request, course_id, course_tenant_id)
        try:
            design = _store(app).read(course_id=course_id, lecture_id=lecture_id)
        except PracticeDesignUnavailable as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        if design is None:
            raise HTTPException(status_code=404, detail="Practice design has not been proposed.")
        return design

    @app.get(
        "/admin/courses/{course_id}/lectures/{lecture_id}/practice-design/readiness",
        response_model=PracticeDesignReadiness,
    )
    def get_practice_design_readiness(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> PracticeDesignReadiness:
        _require_manager(context, request, course_id, course_tenant_id)
        try:
            with locked_course_state(app.state.canvas_workspace.layout.course_root(course_id)):
                source_revision = _source_revision(app, course_id, lecture_id)
                design = _store(app).read(course_id=course_id, lecture_id=lecture_id)
        except PracticeDesignUnavailable as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return PracticeDesignReadiness.current(
            lecture_id=lecture_id,
            source_revision=source_revision,
            design=design,
        )

    @app.put(
        "/admin/courses/{course_id}/lectures/{lecture_id}/practice-design",
        response_model=PracticeDesign,
    )
    def update_practice_design(
        course_id: str,
        lecture_id: str,
        update: PracticeDesignUpdate,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> PracticeDesign:
        _require_manager(context, request, course_id, course_tenant_id)
        layout = app.state.canvas_workspace.layout
        try:
            # Parse unlocked; the store rejects a design whose source revision moved on.
            source, revision, paths = _source_context(app, source_document, course_id, lecture_id)
            with locked_course_state(layout.course_root(course_id)):
                if _source_revision(app, course_id, lecture_id) != revision:
                    raise PracticeDesignStale("Course sources changed. Reload the learning plan.")
                return _store(app).update(
                    course_id=course_id,
                    lecture_id=lecture_id,
                    current_source_revision=revision,
                    update=update,
                    source=source,
                    allowed_source_paths=paths,
                )
        except PracticeDesignStale as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PracticeDesignValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except PracticeDesignApprovalRequired as exc:
            raise HTTPException(
                status_code=404, detail="Practice design has not been proposed."
            ) from exc
        except PracticeDesignUnavailable as exc:
            raise HTTPException(
                status_code=500,
                detail="Stored practice design failed an integrity check.",
            ) from exc

    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/practice-design/approve",
        response_model=PracticeDesign,
    )
    def approve_practice_design(
        course_id: str,
        lecture_id: str,
        approval: PracticeDesignApprovalInput,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> PracticeDesign:
        _require_manager(context, request, course_id, course_tenant_id)
        layout = app.state.canvas_workspace.layout
        try:
            with locked_course_state(layout.course_root(course_id)):
                revision = _source_revision(app, course_id, lecture_id)
                if approval.source_revision != revision:
                    raise HTTPException(
                        status_code=409,
                        detail="The practice design or source revision changed. Reload it.",
                    )
                return _store(app).approve(
                    course_id=course_id,
                    lecture_id=lecture_id,
                    source_revision=revision,
                    design_revision=approval.practice_design_revision,
                    approved_by=context.user_id,
                )
        except PracticeDesignStale as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PracticeDesignApprovalRequired as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    register_learning_intent_routes(
        app,
        course_tenant_id=course_tenant_id,
        source_document=source_document,
        source_context=_source_context,
        source_revision=_source_revision,
        require_manager=_require_manager,
    )
    register_practice_design_proposal_route(
        app, course_tenant_id=course_tenant_id, source_document=source_document
    )
    register_practice_design_review_route(
        app,
        course_tenant_id=course_tenant_id,
        source_document=source_document,
        source_context=_source_context,
        require_manager=_require_manager,
    )


def _store(app: FastAPI) -> PracticeDesignStore:
    return PracticeDesignStore(app.state.canvas_workspace.layout)

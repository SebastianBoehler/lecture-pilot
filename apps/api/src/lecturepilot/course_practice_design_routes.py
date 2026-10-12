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
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.course_practice_design_readiness import PracticeDesignReadiness
from lecturepilot.course_practice_design_store import (
    PracticeDesignStore,
    PracticeDesignUnavailable,
)
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

    register_learning_intent_routes(
        app,
        course_tenant_id=course_tenant_id,
        source_document=source_document,
        source_context=_source_context,
        source_revision=_source_revision,
        require_manager=_require_manager,
    )


def _store(app: FastAPI) -> PracticeDesignStore:
    return PracticeDesignStore(app.state.canvas_workspace.layout)

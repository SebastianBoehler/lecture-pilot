from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.api_auth import request_context, require_course_manager
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.course_practice_design_models import (
    PracticeDesign,
    PracticeDesignApprovalInput,
    PracticeDesignUpdate,
)
from lecturepilot.course_practice_design_store import (
    PracticeDesignApprovalRequired,
    PracticeDesignStale,
    PracticeDesignStore,
    PracticeDesignUnavailable,
)
from lecturepilot.course_practice_design_validation import PracticeDesignValidationError
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.lecture_source_manifest import read_lecture_source_manifest
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError
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

    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/practice-design/proposal",
        response_model=PracticeDesign,
    )
    async def propose_practice_design(
        course_id: str,
        lecture_id: str,
        request: Request,
        refresh: bool = False,
        context: TenantContext = Depends(request_context),
    ) -> PracticeDesign:
        _require_manager(context, request, course_id, course_tenant_id)
        source, revision, paths = _source_context(app, source_document, course_id, lecture_id)
        store = _store(app)
        existing = store.read(course_id=course_id, lecture_id=lecture_id)
        if not refresh and existing is not None and existing.source_revision == revision:
            return existing
        try:
            with app.state.observability.tool_span(
                "course_practice_design",
                course_id=course_id,
                lecture_id=lecture_id,
                source_count=len(paths),
                workload="course_practice_design",
            ) as span:
                with model_usage_scope(
                    actor_user_id=context.user_id,
                    course_id=course_id,
                    workload="course_practice_design",
                ):
                    proposal = await app.state.practice_design_planner.propose(
                        source=source,
                        source_revision=revision,
                        allowed_source_paths=paths,
                    )
                span.set_outputs({"target_count": len(proposal.targets)})
        except ProviderConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ModelExecutionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        layout = app.state.canvas_workspace.layout
        with locked_course_state(layout.course_root(course_id)):
            _, current_revision, current_paths = _source_context(
                app, source_document, course_id, lecture_id
            )
            if current_revision != revision:
                raise HTTPException(
                    status_code=409,
                    detail="Course sources changed while the learning plan was proposed. Generate a new proposal.",
                )
            try:
                return store.save_proposal(
                    course_id=course_id,
                    lecture_id=lecture_id,
                    source_revision=revision,
                    proposal=proposal,
                    allowed_source_paths=current_paths,
                )
            except PracticeDesignValidationError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc

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
        _, revision, paths = _source_context(app, source_document, course_id, lecture_id)
        try:
            return _store(app).update(
                course_id=course_id,
                lecture_id=lecture_id,
                current_source_revision=revision,
                update=update,
                allowed_source_paths=paths,
            )
        except PracticeDesignStale as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PracticeDesignValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

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
        _, revision, _ = _source_context(app, source_document, course_id, lecture_id)
        if approval.source_revision != revision:
            raise HTTPException(
                status_code=409,
                detail="The practice design or source revision changed. Reload it.",
            )
        try:
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


def _store(app: FastAPI) -> PracticeDesignStore:
    return PracticeDesignStore(app.state.canvas_workspace.layout)


def _source_context(
    app: FastAPI,
    source_document: Callable[[str, str], CanvasDocument],
    course_id: str,
    lecture_id: str,
) -> tuple[CanvasDocument, str, tuple[str, ...]]:
    try:
        source = source_document(course_id, lecture_id)
    except SourceBundleCanvasError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    layout = app.state.canvas_workspace.layout
    manifest = read_lecture_source_manifest(
        layout.lecture_source_manifest_path(course_id, lecture_id), course_id, lecture_id
    )
    revision = lecture_source_revision(layout, course_id=course_id, lecture_id=lecture_id)
    paths = tuple(item.path for item in manifest.files)
    if revision is None or not paths:
        raise HTTPException(status_code=409, detail="Confirmed lecture sources are unavailable.")
    return source, revision, paths


def _require_manager(context, request, course_id: str, course_tenant_id: str) -> None:
    require_course_manager(
        context,
        course_tenant_id=course_tenant_id,
        request=request,
        course_id=course_id,
    )

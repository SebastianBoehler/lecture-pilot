from __future__ import annotations

from lecturepilot.course_practice_design_route_context import _source_context, _require_manager

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.api_auth import request_context
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_learning_intent_routes import register_learning_intent_routes
from lecturepilot.course_practice_design_models import (
    PracticeDesign,
    PracticeDesignApprovalInput,
    PracticeDesignUpdate,
    PracticeDesignProposal,
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
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.providers import ProviderConfigurationError
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
                _, source_revision, _ = _source_context(app, source_document, course_id, lecture_id)
                design = _store(app).read(course_id=course_id, lecture_id=lecture_id)
        except PracticeDesignUnavailable as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return PracticeDesignReadiness.current(
            lecture_id=lecture_id,
            source_revision=source_revision,
            design=design,
        )

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
        layout = app.state.canvas_workspace.layout
        store = _store(app)
        try:
            with locked_course_state(layout.course_root(course_id)):
                source, revision, paths = _source_context(
                    app, source_document, course_id, lecture_id
                )
                snapshot = store.snapshot(course_id=course_id, lecture_id=lecture_id)
        except PracticeDesignUnavailable as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        existing = snapshot.design
        if not refresh and existing is not None and existing.source_revision == revision:
            return existing
        if (
            existing is not None
            and existing.approval is not None
            and existing.source_revision == revision
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "This plan is approved in full. Explicitly convert to learning-goal approval "
                    "before asking AI to change its protected teaching details."
                ),
            )
        expected_design_revision = existing.revision if existing is not None else None
        expected_design_approval = existing.approval if existing is not None else None
        expected_design_review = existing.quality_review if existing is not None else None
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
                    initial = (
                        PracticeDesignProposal(
                            lecture_title=existing.lecture_title,
                            objective=existing.objective,
                            planning_context=existing.planning_context,
                            targets=existing.targets,
                        )
                        if existing is not None
                        and existing.targets
                        and existing.source_revision == revision
                        else None
                    )
                    reviewed = await app.state.practice_design_planner.propose(
                        source=source,
                        source_revision=revision,
                        allowed_source_paths=paths,
                        **({"initial": initial} if initial is not None else {}),
                        **(
                            {"protected_intent": existing.learning_intent}
                            if existing
                            and existing.learning_intent
                            and existing.learning_intent.approval
                            else {}
                        ),
                    )
                span.set_outputs({"target_count": len(reviewed.proposal.targets)})
        except ProviderConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ModelExecutionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        with locked_course_state(layout.course_root(course_id)):
            current_source, current_revision, current_paths = _source_context(
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
                    proposal=reviewed.proposal,
                    review=reviewed.review,
                    source=current_source,
                    allowed_source_paths=current_paths,
                    expected_design_revision=expected_design_revision,
                    expected_design_approval=expected_design_approval,
                    expected_design_review=expected_design_review,
                    expected_invalid_digest=snapshot.invalid_digest,
                    expected_learning_intent=existing.learning_intent if existing else None,
                    goals_first=existing is None or existing.learning_intent is not None,
                )
            except PracticeDesignStale as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            except PracticeDesignUnavailable as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc
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
        layout = app.state.canvas_workspace.layout
        try:
            with locked_course_state(layout.course_root(course_id)):
                source, revision, paths = _source_context(
                    app, source_document, course_id, lecture_id
                )
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
                _, revision, _ = _source_context(app, source_document, course_id, lecture_id)
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
        require_manager=_require_manager,
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

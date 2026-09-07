from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from lecturepilot.api_auth import request_context, require_course_manager
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.client_contract import (
    CLIENT_CONTRACT_HEADER,
    require_current_client_contract,
)
from lecturepilot.course_canvas_generation import generate_course_canvas_draft
from lecturepilot.course_canvas_generation_cancel import cancel_canvas_generation
from lecturepilot.authoring_status import read_authoring_metrics
from lecturepilot.authoring_session import has_resumable_session
from lecturepilot import course_canvas_generation_ownership as ownership_store
from lecturepilot.course_canvas_generation_failures import find_latest_canvas_generation
from lecturepilot.course_canvas_generation_http import run_canvas_generation_request
from lecturepilot.course_canvas_generation_jobs import CanvasGenerationJob, CanvasGenerationStore
from lecturepilot.course_canvas_async_response import accepted_generation_response
from lecturepilot.course_canvas_generation_response import CanvasGenerationStatusResponse
from lecturepilot.course_canvas_generation_service import (
    CANVAS_GENERATION_LEASE_SECONDS,
    validate_generation_request_key,
)
from lecturepilot.course_canvas_store import InvalidCanvasDraftError
from lecturepilot.course_practice_design_store import (
    PracticeDesignApprovalRequired,
    PracticeDesignStale,
    PracticeDesignUnavailable,
)
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError
from lecturepilot.tenancy import TenantContext


def register_course_canvas_draft_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    source_document: Callable[[str, str], CanvasDocument],
) -> None:
    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/draft/cancel",
        response_model=CanvasGenerationStatusResponse,
        response_model_exclude={"canvas": {"workspace_path"}},
    )
    async def cancel_draft_generation(
        course_id: str,
        lecture_id: str,
        request: Request,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
        client_contract: Annotated[str | None, Header(alias=CLIENT_CONTRACT_HEADER)] = None,
        context: TenantContext = Depends(request_context),
    ):
        _require_owner(request, context, course_id, course_tenant_id)
        require_current_client_contract(client_contract)
        job = await cancel_canvas_generation(
            app=app,
            store=_store(app),
            course_id=course_id,
            lecture_id=lecture_id,
            actor_user_id=context.user_id,
            request_key=_request_key(idempotency_key),
        )
        if job is None:
            raise HTTPException(status_code=404, detail="Canvas generation was not found.")
        return CanvasGenerationStatusResponse.model_validate(job.model_dump())

    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/draft",
        response_model=CanvasDocument,
        response_model_exclude={"workspace_path"},
    )
    async def draft_course_canvas(
        course_id: str,
        lecture_id: str,
        request: Request,
        response: Response,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
        client_contract: Annotated[str | None, Header(alias=CLIENT_CONTRACT_HEADER)] = None,
        context: TenantContext = Depends(request_context),
    ) -> CanvasDocument | JSONResponse:
        _require_owner(request, context, course_id, course_tenant_id)
        require_current_client_contract(client_contract)
        request_key = _request_key(idempotency_key)
        _require_current_practice_design(app, course_id, lecture_id, source_document)
        store = _store(app)
        outcome = await run_canvas_generation_request(
            wait_for_completion=request.headers.get("Prefer") != "respond-async",
            app=app,
            store=store,
            course_id=course_id,
            lecture_id=lecture_id,
            context=context,
            request_key=request_key,
            generate=lambda generation_id, attempt: generate_course_canvas_draft(
                app,
                course_id=course_id,
                lecture_id=lecture_id,
                context=context,
                source_document=source_document,
                generation_id=generation_id,
                attempt=attempt,
            ),
        )
        if isinstance(outcome, CanvasGenerationJob):
            return accepted_generation_response(outcome)
        response.headers["X-Generation-Id"] = outcome.job.generation_id
        return outcome.canvas

    @app.get(
        "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/draft/status",
        response_model=CanvasGenerationStatusResponse,
        response_model_exclude={"canvas": {"workspace_path"}},
    )
    def course_canvas_generation_status(
        course_id: str,
        lecture_id: str,
        request: Request,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
        context: TenantContext = Depends(request_context),
    ) -> CanvasGenerationStatusResponse:
        _require_owner(request, context, course_id, course_tenant_id)
        job = _store(app).read(
            course_id=course_id,
            lecture_id=lecture_id,
            actor_user_id=context.user_id,
            request_key=_request_key(idempotency_key),
        )
        if job is None:
            raise HTTPException(status_code=404, detail="Canvas generation was not found.")
        if (
            job.status == "running"
            and (datetime.now(UTC) - job.updated_at).total_seconds()
            > CANVAS_GENERATION_LEASE_SECONDS
        ):
            raise HTTPException(
                status_code=503,
                detail="Generation service unavailable; retry to resume saved work.",
            )
        return CanvasGenerationStatusResponse(
            generation_id=job.generation_id,
            status=job.status,
            attempt=job.attempt,
            updated_at=job.updated_at,
            error_code=job.error_code,
            error_detail=job.error_detail,
            repairable=(
                job.error_code == "canvas_generation_repairable_error"
                or has_resumable_session(app.state.canvas_workspace.layout, job)
            ),
            canvas=job.canvas,
            authoring_metrics=read_authoring_metrics(app.state.canvas_workspace.layout, job),
        )

    @app.get(
        "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/draft",
        response_model=CanvasDocument,
        response_model_exclude={"workspace_path"},
    )
    def preview_course_canvas_draft(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CanvasDocument:
        try:
            _require_owner(request, context, course_id, course_tenant_id)
            return app.state.canvas_workspace.read_course_canvas_draft(
                course_id=course_id,
                lecture_id=lecture_id,
            )
        except InvalidCanvasDraftError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except CanvasWorkspaceError as exc:
            generation = find_latest_canvas_generation(
                app.state.canvas_workspace.layout,
                course_id=course_id,
                lecture_id=lecture_id,
                actor_user_id=context.user_id,
            )
            headers = {"X-Generation-Status": generation.status} if generation else {}
            if generation and (
                generation.error_code == "canvas_generation_repairable_error"
                or has_resumable_session(app.state.canvas_workspace.layout, generation)
            ):
                headers["X-Generation-Repairable"] = "true"
            detail = generation.error_detail if generation and generation.error_detail else str(exc)
            raise HTTPException(status_code=404, detail=detail, headers=headers) from exc


def _request_key(value: str | None) -> str:
    if value is None:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required.")
    try:
        return validate_generation_request_key(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _store(app: FastAPI) -> CanvasGenerationStore:
    return CanvasGenerationStore(
        app.state.canvas_workspace.layout,
        lease_seconds=CANVAS_GENERATION_LEASE_SECONDS,
    )


def _require_owner(
    request: Request, context: TenantContext, course_id: str, tenant_id: str
) -> None:
    require_course_manager(
        context,
        course_tenant_id=tenant_id,
        request=request,
        course_id=course_id,
    )


def _require_current_practice_design(
    app: FastAPI,
    course_id: str,
    lecture_id: str,
    source_document: Callable[[str, str], CanvasDocument],
) -> None:
    try:
        ownership_store.require_generation_practice_design(
            app.state.canvas_workspace.layout,
            app.state.canvas_workspace.course_media_root(course_id),
            source_document,
            course_id=course_id,
            lecture_id=lecture_id,
        )
    except (
        ownership_store.CanvasGenerationOwnershipError,
        PracticeDesignApprovalRequired,
        PracticeDesignStale,
        PracticeDesignUnavailable,
        SourceBundleCanvasError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

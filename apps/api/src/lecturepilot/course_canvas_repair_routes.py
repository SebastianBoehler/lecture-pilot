from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response

from lecturepilot.api_auth import request_context, require_course_manager
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.client_contract import CLIENT_CONTRACT_HEADER, require_current_client_contract
from lecturepilot.course_canvas_generation import generate_course_canvas_draft
from lecturepilot.course_canvas_generation_failures import find_latest_canvas_failure
from lecturepilot.course_canvas_generation_http import run_canvas_generation_request
from lecturepilot.course_canvas_generation_jobs import CanvasGenerationStore
from lecturepilot.course_canvas_generation_service import (
    CANVAS_GENERATION_LEASE_SECONDS,
    validate_generation_request_key,
)
from lecturepilot.tenancy import TenantContext


def register_course_canvas_repair_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    source_document: Callable[[str, str], CanvasDocument],
) -> None:
    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/draft/repair",
        response_model=CanvasDocument,
        response_model_exclude={"workspace_path"},
    )
    async def repair_course_canvas(
        course_id: str,
        lecture_id: str,
        request: Request,
        response: Response,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
        client_contract: Annotated[str | None, Header(alias=CLIENT_CONTRACT_HEADER)] = None,
        context: TenantContext = Depends(request_context),
    ) -> CanvasDocument:
        require_course_manager(
            context,
            course_tenant_id=course_tenant_id,
            request=request,
            course_id=course_id,
        )
        require_current_client_contract(client_contract)
        request_key = _request_key(idempotency_key)
        store = CanvasGenerationStore(
            app.state.canvas_workspace.layout,
            lease_seconds=CANVAS_GENERATION_LEASE_SECONDS,
        )
        failure = find_latest_canvas_failure(
            store.layout,
            course_id=course_id,
            lecture_id=lecture_id,
            actor_user_id=context.user_id,
        )
        if failure is None or not failure.error_detail:
            raise HTTPException(
                status_code=409,
                detail="No actionable failed generation is available for AI repair.",
            )
        outcome = await run_canvas_generation_request(
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
                repair_failure_code=failure.error_code or "generation_failed",
                repair_failure_detail=failure.error_detail,
            ),
        )
        response.headers["X-Generation-Id"] = outcome.job.generation_id
        response.headers["X-Repair-Source-Generation-Id"] = failure.generation_id
        return outcome.canvas


def _request_key(value: str | None) -> str:
    if value is None:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required.")
    try:
        return validate_generation_request_key(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

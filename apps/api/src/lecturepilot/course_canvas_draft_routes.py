from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response

from lecturepilot.api_auth import request_context, require_course_manager
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.client_contract import (
    CLIENT_CONTRACT_HEADER,
    require_current_client_contract,
)
from lecturepilot.course_canvas_generation import generate_course_canvas_draft
from lecturepilot.course_canvas_generation_jobs import (
    CanvasGenerationStatusResponse,
    CanvasGenerationStore,
    CanvasGenerationStoreError,
)
from lecturepilot.course_canvas_generation_service import (
    CANVAS_GENERATION_LEASE_SECONDS,
    CanvasGenerationInProgressError,
    CanvasGenerationReplayError,
    CanvasGenerationTimeoutError,
    run_idempotent_canvas_generation,
    validate_generation_request_key,
)
from lecturepilot.course_canvas_store import InvalidCanvasDraftError
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError
from lecturepilot.tenancy import TenantContext


logger = logging.getLogger(__name__)


def register_course_canvas_draft_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    source_document: Callable[[str, str], CanvasDocument],
) -> None:
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
    ) -> CanvasDocument:
        _require_owner(request, context, course_id, course_tenant_id)
        require_current_client_contract(client_contract)
        request_key = _request_key(idempotency_key)
        store = _store(app)
        try:
            outcome = await run_idempotent_canvas_generation(
                app=app,
                store=store,
                course_id=course_id,
                lecture_id=lecture_id,
                actor_user_id=context.user_id,
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
            response.headers["X-Generation-Id"] = outcome.job.generation_id
            return outcome.canvas
        except InvalidCanvasDraftError as exc:
            raise _generation_error(
                502, str(exc), store, context, course_id, lecture_id, request_key
            ) from exc
        except CanvasWorkspaceError as exc:
            raise _generation_error(
                404, str(exc), store, context, course_id, lecture_id, request_key
            ) from exc
        except SourceBundleCanvasError as exc:
            raise _generation_error(
                400, str(exc), store, context, course_id, lecture_id, request_key
            ) from exc
        except ProviderConfigurationError as exc:
            raise _generation_error(
                503, str(exc), store, context, course_id, lecture_id, request_key
            ) from exc
        except ModelExecutionError as exc:
            raise _generation_error(
                502, str(exc), store, context, course_id, lecture_id, request_key
            ) from exc
        except CanvasGenerationTimeoutError as exc:
            raise _generation_error(
                504,
                "Canvas generation timed out.",
                store,
                context,
                course_id,
                lecture_id,
                request_key,
            ) from exc
        except CanvasGenerationInProgressError as exc:
            raise _generation_error(
                503,
                "Canvas generation is still in progress.",
                store,
                context,
                course_id,
                lecture_id,
                request_key,
                headers={"Retry-After": "5"},
            ) from exc
        except CanvasGenerationReplayError as exc:
            raise _replayed_failure(
                exc, store, context, course_id, lecture_id, request_key
            ) from exc
        except CanvasGenerationStoreError as exc:
            raise HTTPException(
                status_code=500, detail="Canvas generation state could not be read."
            ) from exc
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 - return a safe API error and retain traceback.
            logger.exception("Unexpected course canvas generation failure")
            raise _generation_error(
                502,
                "Canvas generation failed unexpectedly.",
                store,
                context,
                course_id,
                lecture_id,
                request_key,
            ) from exc

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
        return CanvasGenerationStatusResponse(
            generation_id=job.generation_id,
            status=job.status,
            attempt=job.attempt,
            updated_at=job.updated_at,
            error_code=job.error_code,
            canvas=job.canvas,
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
            raise HTTPException(status_code=404, detail=str(exc)) from exc


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


def _replayed_failure(
    exc: CanvasGenerationReplayError,
    store: CanvasGenerationStore,
    context: TenantContext,
    course_id: str,
    lecture_id: str,
    request_key: str,
) -> HTTPException:
    status = {
        "canvas_workspace_error": 404,
        "source_bundle_canvas_error": 400,
        "provider_configuration_error": 503,
        "interrupted": 503,
        "timeout": 504,
    }.get(exc.error_code, 502)
    return _generation_error(
        status,
        "The previous canvas generation attempt failed. Start a new retry.",
        store,
        context,
        course_id,
        lecture_id,
        request_key,
    )


def _generation_error(
    status_code: int,
    detail: str,
    store: CanvasGenerationStore,
    context: TenantContext,
    course_id: str,
    lecture_id: str,
    request_key: str,
    *,
    headers: dict[str, str] | None = None,
) -> HTTPException:
    response_headers = dict(headers or {})
    try:
        job = store.read(
            course_id=course_id,
            lecture_id=lecture_id,
            actor_user_id=context.user_id,
            request_key=request_key,
        )
    except CanvasGenerationStoreError:
        job = None
    if job is not None:
        response_headers["X-Generation-Id"] = job.generation_id
        response_headers["X-Generation-Status"] = job.status
    return HTTPException(status_code=status_code, detail=detail, headers=response_headers)


def _require_owner(
    request: Request, context: TenantContext, course_id: str, tenant_id: str
) -> None:
    require_course_manager(
        context,
        course_tenant_id=tenant_id,
        request=request,
        course_id=course_id,
    )

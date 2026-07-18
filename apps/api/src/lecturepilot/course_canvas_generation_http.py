from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
from typing import Any

from fastapi import HTTPException

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_generation_jobs import (
    CanvasGenerationStore,
    CanvasGenerationStoreError,
)
from lecturepilot.course_canvas_generation_service import (
    CanvasGenerationInProgressError,
    CanvasGenerationOutcome,
    CanvasGenerationReplayError,
    CanvasGenerationTimeoutError,
    run_idempotent_canvas_generation,
)
from lecturepilot.course_canvas_store import InvalidCanvasDraftError
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError
from lecturepilot.tenancy import TenantContext


logger = logging.getLogger(__name__)


async def run_canvas_generation_request(
    *,
    app: Any,
    store: CanvasGenerationStore,
    course_id: str,
    lecture_id: str,
    context: TenantContext,
    request_key: str,
    generate: Callable[[str, int], Awaitable[CanvasDocument]],
) -> CanvasGenerationOutcome:
    try:
        return await run_idempotent_canvas_generation(
            app=app,
            store=store,
            course_id=course_id,
            lecture_id=lecture_id,
            actor_user_id=context.user_id,
            request_key=request_key,
            generate=generate,
        )
    except InvalidCanvasDraftError as exc:
        raise _generation_error(502, str(exc), store, context, request_key, course_id, lecture_id)
    except CanvasWorkspaceError as exc:
        raise _generation_error(404, str(exc), store, context, request_key, course_id, lecture_id)
    except SourceBundleCanvasError as exc:
        raise _generation_error(400, str(exc), store, context, request_key, course_id, lecture_id)
    except CanvasGenerationRepairableError as exc:
        raise _generation_error(
            503,
            str(exc),
            store,
            context,
            request_key,
            course_id,
            lecture_id,
            headers={"X-Generation-Repairable": "true"},
        )
    except ProviderConfigurationError as exc:
        raise _generation_error(503, str(exc), store, context, request_key, course_id, lecture_id)
    except ModelExecutionError as exc:
        raise _generation_error(502, str(exc), store, context, request_key, course_id, lecture_id)
    except CanvasGenerationTimeoutError as exc:
        raise _generation_error(
            504, "Canvas generation timed out.", store, context, request_key, course_id, lecture_id
        ) from exc
    except CanvasGenerationInProgressError as exc:
        raise _generation_error(
            503,
            "Canvas generation is still in progress.",
            store,
            context,
            request_key,
            course_id,
            lecture_id,
            headers={"Retry-After": "5"},
        ) from exc
    except CanvasGenerationReplayError as exc:
        status = {
            "canvas_workspace_error": 404,
            "source_bundle_canvas_error": 400,
            "provider_configuration_error": 503,
            "interrupted": 503,
            "timeout": 504,
        }.get(exc.error_code, 502)
        raise _generation_error(
            status,
            "The previous canvas generation attempt failed. Start a new retry.",
            store,
            context,
            request_key,
            course_id,
            lecture_id,
        ) from exc
    except CanvasGenerationStoreError as exc:
        raise HTTPException(
            status_code=500, detail="Canvas generation state could not be read."
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - retain traceback but return a safe API error.
        logger.exception("Unexpected course canvas generation failure")
        raise _generation_error(
            502,
            "Canvas generation failed unexpectedly.",
            store,
            context,
            request_key,
            course_id,
            lecture_id,
        ) from exc


def _generation_error(
    status_code: int,
    detail: str,
    store: CanvasGenerationStore,
    context: TenantContext,
    request_key: str,
    course_id: str,
    lecture_id: str,
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

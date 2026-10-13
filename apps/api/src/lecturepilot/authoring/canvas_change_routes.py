"""Professor change requests: regenerate only the sections a request concerns."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from lecturepilot.authoring.canvas_change_base import (
    ChangeBase,
    ChangeRequestUnavailable,
    change_request_base,
)
from lecturepilot.authoring.canvas_change_generation import generate_canvas_change
from lecturepilot.authoring.canvas_change_models import (
    CanvasChangeInput,
    CanvasChangeOptions,
    CanvasChangeSection,
    latest_change_record,
)
from lecturepilot.authoring.canvas_change_selection import selectable_sections
from lecturepilot.authoring.course_canvas_async_response import accepted_generation_response
from lecturepilot.authoring.course_canvas_generation_http import run_canvas_generation_request
from lecturepilot.authoring.course_canvas_generation_jobs import (
    CanvasGenerationJob,
    CanvasGenerationStore,
)
from lecturepilot.authoring.course_canvas_generation_precheck import require_current_practice_design
from lecturepilot.authoring.course_canvas_generation_service import (
    CANVAS_GENERATION_LEASE_SECONDS,
    validate_generation_request_key,
)
from lecturepilot.canvas.canvas_models import CanvasDocument
from lecturepilot.core.client_contract import (
    CLIENT_CONTRACT_HEADER,
    require_current_client_contract,
)
from lecturepilot.identity.api_auth import request_context, require_course_manager
from lecturepilot.identity.tenancy import TenantContext

PATH = "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/change-request"


def register_canvas_change_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    source_document: Callable[[str, str], CanvasDocument],
) -> None:
    def base(course_id: str, lecture_id: str) -> ChangeBase:
        try:
            return change_request_base(
                app.state.canvas_workspace.layout, course_id=course_id, lecture_id=lecture_id
            )
        except ChangeRequestUnavailable as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get(PATH, response_model=CanvasChangeOptions)
    async def canvas_change_options(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CanvasChangeOptions:
        require_course_manager(
            context, course_tenant_id=course_tenant_id, request=request, course_id=course_id
        )

        def options() -> CanvasChangeOptions:
            current = base(course_id, lecture_id)
            return CanvasChangeOptions(
                base=current.kind,
                sections=[
                    CanvasChangeSection(id=section.id, title=section.title)
                    for section in selectable_sections(current.document)
                ],
                latest=latest_change_record(
                    app.state.canvas_workspace.layout, course_id=course_id, lecture_id=lecture_id
                ),
            )

        return await run_in_threadpool(options)

    @app.post(PATH, response_model=CanvasDocument, response_model_exclude={"workspace_path"})
    async def request_canvas_change(
        course_id: str,
        lecture_id: str,
        change: CanvasChangeInput,
        request: Request,
        response: Response,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
        client_contract: Annotated[str | None, Header(alias=CLIENT_CONTRACT_HEADER)] = None,
        context: TenantContext = Depends(request_context),
    ) -> CanvasDocument | JSONResponse:
        require_course_manager(
            context, course_tenant_id=course_tenant_id, request=request, course_id=course_id
        )
        require_current_client_contract(client_contract)
        request_key = _request_key(idempotency_key)
        store = CanvasGenerationStore(
            app.state.canvas_workspace.layout, lease_seconds=CANVAS_GENERATION_LEASE_SECONDS
        )
        replay = await run_in_threadpool(
            lambda: store.read(
                course_id=course_id,
                lecture_id=lecture_id,
                actor_user_id=context.user_id,
                request_key=request_key,
            )
        )
        if replay is None:  # A retry of an accepted request replays it instead of re-checking.
            current = await run_in_threadpool(base, course_id, lecture_id)
            await require_current_practice_design(app, course_id, lecture_id)
            known = {section.id for section in selectable_sections(current.document)}
            unknown = [s for s in change.named_sections() if s not in known]
            if unknown:
                raise HTTPException(
                    status_code=422, detail=f"Unknown section for this lecture: {unknown[0]}"
                )
        outcome = await run_canvas_generation_request(
            wait_for_completion=request.headers.get("Prefer") != "respond-async",
            app=app,
            store=store,
            course_id=course_id,
            lecture_id=lecture_id,
            context=context,
            request_key=request_key,
            generate=lambda generation_id, attempt: generate_canvas_change(
                app,
                course_id=course_id,
                lecture_id=lecture_id,
                context=context,
                source_document=source_document,
                change=change,
                generation_id=generation_id,
                attempt=attempt,
            ),
        )
        if isinstance(outcome, CanvasGenerationJob):
            return accepted_generation_response(outcome)
        response.headers["X-Generation-Id"] = outcome.job.generation_id
        return outcome.canvas


def _request_key(value: str | None) -> str:
    if value is None:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required.")
    try:
        return validate_generation_request_key(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

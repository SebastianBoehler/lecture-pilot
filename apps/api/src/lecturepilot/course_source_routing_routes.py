from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.document_converter_client import DocumentConverterError
from lecturepilot.api_auth import request_context, require_course_manager
from lecturepilot.course_schedule_store import read_course_workspace
from lecturepilot.course_source_routing import (
    SourceRoutingError,
    SourceRoutingProposalRequired,
    StaleSourceRoutingError,
    confirm_source_routing,
    review_source_routing,
    save_source_routing_proposal,
    source_revision,
)
from lecturepilot.course_source_routing_models import (
    CourseSourceRoutingInput,
    CourseSourceRoutingManifest,
)
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.source_index import refresh_course_source_index
from lecturepilot.source_document_normalization import normalize_selected_documents
from lecturepilot.tenancy import TenantContext


def register_course_source_routing_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
) -> None:
    @app.get(
        "/admin/courses/{course_id}/source-routing",
        response_model=CourseSourceRoutingManifest,
    )
    def get_course_source_routing(
        course_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CourseSourceRoutingManifest:
        _require_manager(context, request, course_id, course_tenant_id)
        layout = app.state.canvas_workspace.layout
        try:
            with locked_course_state(layout.course_root(course_id)):
                index = _refresh_index(layout, course_id)
                lectures = _lectures(app, course_id)
                return review_source_routing(
                    course_id=course_id,
                    index=index,
                    lectures=lectures,
                    routing_path=layout.course_source_routing_path(course_id),
                )
        except SourceRoutingProposalRequired as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post(
        "/admin/courses/{course_id}/source-routing/proposal",
        response_model=CourseSourceRoutingManifest,
    )
    async def propose_course_source_routing(
        course_id: str,
        request: Request,
        refresh: bool = False,
        context: TenantContext = Depends(request_context),
    ) -> CourseSourceRoutingManifest:
        _require_manager(context, request, course_id, course_tenant_id)
        layout = app.state.canvas_workspace.layout
        with locked_course_state(layout.course_root(course_id)):
            index = _refresh_index(layout, course_id)
            lectures = _lectures(app, course_id)
            if not refresh:
                try:
                    return review_source_routing(
                        course_id=course_id,
                        index=index,
                        lectures=lectures,
                        routing_path=layout.course_source_routing_path(course_id),
                    )
                except SourceRoutingProposalRequired:
                    pass
            expected_revision = source_revision(index, lectures)

        try:
            normalized_root = layout.course_normalized_dir(course_id)
            normalize_selected_documents(
                files=[item.as_bundle_file() for item in index.files],
                source_root=layout.course_uploads_dir(course_id),
                normalized_root=normalized_root,
            )
            with app.state.observability.tool_span(
                "course_source_routing",
                course_id=course_id,
                source_count=len(index.files),
                workload="course_source_routing",
            ) as span:
                with model_usage_scope(
                    actor_user_id=context.user_id,
                    course_id=course_id,
                    workload="course_source_routing",
                ):
                    routes = await app.state.source_routing_planner.propose_routes(
                        course_id=course_id,
                        files=index.files,
                        lectures=lectures,
                        roots=[
                            *app.state.canvas_workspace.source_bundle_roots(
                                course_id, include_seeded_materials=False
                            ),
                            normalized_root,
                        ],
                    )
                span.set_outputs({"route_count": len(routes)})
        except ProviderConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ModelExecutionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except DocumentConverterError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        with locked_course_state(layout.course_root(course_id)):
            current_index = _refresh_index(layout, course_id)
            current_lectures = _lectures(app, course_id)
            if source_revision(current_index, current_lectures) != expected_revision:
                raise HTTPException(
                    status_code=409,
                    detail="Course sources changed while the agent assigned them. Generate a new proposal.",
                )
            return save_source_routing_proposal(
                course_id=course_id,
                index=current_index,
                lectures=current_lectures,
                routing_path=layout.course_source_routing_path(course_id),
                routes=routes,
            )

    @app.put(
        "/admin/courses/{course_id}/source-routing",
        response_model=CourseSourceRoutingManifest,
    )
    def put_course_source_routing(
        course_id: str,
        routing: CourseSourceRoutingInput,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CourseSourceRoutingManifest:
        _require_manager(context, request, course_id, course_tenant_id)
        layout = app.state.canvas_workspace.layout
        try:
            with locked_course_state(layout.course_root(course_id)):
                return confirm_source_routing(
                    course_id=course_id,
                    index=_refresh_index(layout, course_id),
                    lectures=_lectures(app, course_id),
                    routing_path=layout.course_source_routing_path(course_id),
                    routing=routing,
                )
        except StaleSourceRoutingError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except SourceRoutingError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


def _refresh_index(layout, course_id: str):
    return refresh_course_source_index(
        course_id=course_id,
        uploads_dir=layout.course_uploads_dir(course_id),
        index_path=layout.course_source_index_path(course_id),
    )


def _lectures(app: FastAPI, course_id: str):
    workspace = read_course_workspace(
        app.state.canvas_workspace.course_media_root(course_id), course_id
    )
    if workspace is None:
        raise HTTPException(
            status_code=409, detail="Define the lecture schedule before routing sources."
        )
    return workspace.lectures


def _require_manager(context, request, course_id: str, course_tenant_id: str) -> None:
    require_course_manager(
        context,
        course_tenant_id=course_tenant_id,
        request=request,
        course_id=course_id,
    )

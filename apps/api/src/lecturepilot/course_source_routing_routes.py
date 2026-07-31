from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.api_auth import request_context, require_course_manager
from lecturepilot.course_schedule_store import read_course_workspace
from lecturepilot.course_source_routing import (
    SourceRoutingError,
    StaleSourceRoutingError,
    confirm_source_routing,
    review_source_routing,
)
from lecturepilot.course_source_routing_models import (
    CourseSourceRoutingInput,
    CourseSourceRoutingManifest,
)
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.source_index import refresh_course_source_index
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
        with locked_course_state(layout.course_root(course_id)):
            index = _refresh_index(layout, course_id)
            lectures = _lectures(app, course_id)
            return review_source_routing(
                course_id=course_id,
                index=index,
                lectures=lectures,
                routing_path=layout.course_source_routing_path(course_id),
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

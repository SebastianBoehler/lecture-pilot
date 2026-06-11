from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query

from lecturepilot.api_auth import request_context, require_course_manager
from lecturepilot.course_media import add_youtube_selection, clear_course_media, list_course_media
from lecturepilot.models import (
    Course,
    Lecture,
    YoutubeSearchResponse,
    YoutubeSelectionInput,
    YoutubeSelectionResult,
)
from lecturepilot.tenancy import TenantContext
from lecturepilot.youtube_discovery import YoutubeDiscoveryError


def register_admin_media_routes(
    app: FastAPI,
    *,
    course: Course,
    lectures: list[Lecture],
    course_tenant_id: str,
) -> None:
    lecture_ids = {lecture.id for lecture in lectures}

    @app.get("/admin/courses/{course_id}/media/youtube/search", response_model=YoutubeSearchResponse)
    def search_youtube_media(
        course_id: str,
        q: str = Query(..., min_length=1, max_length=300),
        max_results: int = Query(default=5, ge=1, le=10),
        context: TenantContext = Depends(request_context),
    ) -> YoutubeSearchResponse:
        require_course_manager(context, course_tenant_id=course_tenant_id)
        try:
            return app.state.youtube_discovery.search(q, max_results=max_results)
        except YoutubeDiscoveryError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/media/youtube",
        response_model=YoutubeSelectionResult,
    )
    def include_youtube_media(
        course_id: str,
        lecture_id: str,
        selection: YoutubeSelectionInput,
        context: TenantContext = Depends(request_context),
    ) -> YoutubeSelectionResult:
        _assert_seeded_lecture(course_id, lecture_id, course, lecture_ids)
        require_course_manager(context, course_tenant_id=course_tenant_id)
        try:
            return add_youtube_selection(
                material_root=_course_media_root(app, course_id),
                course_id=course_id,
                lecture_id=lecture_id,
                selection=selection,
                approved_by=context.user_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/admin/courses/{course_id}/lectures/{lecture_id}/media/youtube")
    def list_youtube_media(
        course_id: str,
        lecture_id: str,
        context: TenantContext = Depends(request_context),
    ) -> list[dict]:
        _assert_seeded_lecture(course_id, lecture_id, course, lecture_ids)
        require_course_manager(context, course_tenant_id=course_tenant_id)
        return list_course_media(
            material_root=_course_media_root(app, course_id),
            course_id=course_id,
            lecture_id=lecture_id,
        )

    @app.delete("/admin/courses/{course_id}/media/youtube")
    def clear_youtube_media(
        course_id: str,
        context: TenantContext = Depends(request_context),
    ) -> dict[str, int]:
        require_course_manager(context, course_tenant_id=course_tenant_id)
        return {
            "deleted": clear_course_media(
                material_root=_course_media_root(app, course_id),
                course_id=course_id,
            )
        }


def _assert_seeded_lecture(
    course_id: str,
    lecture_id: str,
    course: Course,
    lecture_ids: set[str],
) -> None:
    if course_id == course.id and lecture_id not in lecture_ids:
        raise HTTPException(status_code=404, detail="Lecture not found.")


def _course_media_root(app: FastAPI, course_id: str):
    workspace = app.state.canvas_workspace
    if hasattr(workspace, "course_media_root"):
        return workspace.course_media_root(course_id)
    return workspace.material_root

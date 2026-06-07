from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException, Query

from lecturepilot.course_media import add_youtube_selection, list_course_media
from lecturepilot.models import (
    Course,
    Lecture,
    TenantRole,
    YoutubeSearchResponse,
    YoutubeSelectionInput,
    YoutubeSelectionResult,
)
from lecturepilot.tenancy import TenantAccessError, TenantContext, assert_can_manage_course
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
        x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
        x_user_id: str = Header(..., alias="X-User-Id"),
        x_user_role: TenantRole = Header(..., alias="X-User-Role"),
    ) -> YoutubeSearchResponse:
        _assert_course(course_id, course)
        _assert_professor(x_tenant_id, x_user_id, x_user_role, course_tenant_id)
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
        x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
        x_user_id: str = Header(..., alias="X-User-Id"),
        x_user_role: TenantRole = Header(..., alias="X-User-Role"),
    ) -> YoutubeSelectionResult:
        _assert_course(course_id, course)
        _assert_lecture(lecture_id, lecture_ids)
        _assert_professor(x_tenant_id, x_user_id, x_user_role, course_tenant_id)
        try:
            return add_youtube_selection(
                material_root=app.state.canvas_workspace.material_root,
                course_id=course_id,
                lecture_id=lecture_id,
                selection=selection,
                approved_by=x_user_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/admin/courses/{course_id}/lectures/{lecture_id}/media/youtube")
    def list_youtube_media(
        course_id: str,
        lecture_id: str,
        x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
        x_user_id: str = Header(..., alias="X-User-Id"),
        x_user_role: TenantRole = Header(..., alias="X-User-Role"),
    ) -> list[dict]:
        _assert_course(course_id, course)
        _assert_lecture(lecture_id, lecture_ids)
        _assert_professor(x_tenant_id, x_user_id, x_user_role, course_tenant_id)
        return list_course_media(
            material_root=app.state.canvas_workspace.material_root,
            course_id=course_id,
            lecture_id=lecture_id,
        )


def _assert_professor(
    tenant_id: str,
    user_id: str,
    role: TenantRole,
    course_tenant_id: str,
) -> None:
    context = TenantContext(tenant_id=tenant_id, user_id=user_id, roles=frozenset({role}))
    try:
        assert_can_manage_course(context, course_tenant_id=course_tenant_id)
    except TenantAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _assert_course(course_id: str, course: Course) -> None:
    if course_id != course.id:
        raise HTTPException(status_code=404, detail="Course not found.")


def _assert_lecture(lecture_id: str, lecture_ids: set[str]) -> None:
    if lecture_id not in lecture_ids:
        raise HTTPException(status_code=404, detail="Lecture not found.")

from collections.abc import Callable
from fastapi import FastAPI, HTTPException
from lecturepilot.api_auth import require_course_manager
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.lecture_source_manifest import read_lecture_source_manifest
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError


def _source_context(
    app: FastAPI,
    source_document: Callable[[str, str], CanvasDocument],
    course_id: str,
    lecture_id: str,
) -> tuple[CanvasDocument, str, tuple[str, ...]]:
    try:
        source = source_document(course_id, lecture_id)
    except SourceBundleCanvasError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    layout = app.state.canvas_workspace.layout
    manifest = read_lecture_source_manifest(
        layout.lecture_source_manifest_path(course_id, lecture_id), course_id, lecture_id
    )
    revision = lecture_source_revision(layout, course_id=course_id, lecture_id=lecture_id)
    paths = tuple(item.path for item in manifest.files)
    if revision is None or not paths:
        raise HTTPException(status_code=409, detail="Confirmed lecture sources are unavailable.")
    return source, revision, paths


def _require_manager(context, request, course_id: str, course_tenant_id: str) -> None:
    require_course_manager(
        context,
        course_tenant_id=course_tenant_id,
        request=request,
        course_id=course_id,
    )

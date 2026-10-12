from collections.abc import Callable
from fastapi import FastAPI, HTTPException
from lecturepilot.identity.api_auth import require_course_manager
from lecturepilot.canvas.canvas_models import CanvasDocument
from lecturepilot.sources.course_builder_source import course_builder_source_revision
from lecturepilot.authoring.course_canvas_repairs import lecture_source_revision
from lecturepilot.sources.lecture_source_manifest import read_lecture_source_manifest
from lecturepilot.sources.source_bundle_canvas import SourceBundleCanvasError


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


def _source_revision(app: FastAPI, course_id: str, lecture_id: str) -> str:
    """Revision checks hash confirmed files; they never parse or import documents."""
    try:
        revision = course_builder_source_revision(app, course_id, lecture_id)
    except SourceBundleCanvasError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if revision is None:
        raise HTTPException(status_code=409, detail="Confirmed lecture sources are unavailable.")
    return revision


def _require_manager(context, request, course_id: str, course_tenant_id: str) -> None:
    require_course_manager(
        context,
        course_tenant_id=course_tenant_id,
        request=request,
        course_id=course_id,
    )

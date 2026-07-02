from __future__ import annotations

from fastapi import FastAPI

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.source_bundle import scan_source_bundle
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError, import_source_bundle_canvas


def scan_source_bundles(roots) -> list:
    files_by_path = {}
    for root in roots:
        for item in scan_source_bundle(root):
            files_by_path.setdefault(item.path, item)
    return list(files_by_path.values())


def course_builder_source_document(app: FastAPI, course_id: str, lecture_id: str) -> CanvasDocument:
    workspace = app.state.canvas_workspace
    workspace_path = f"course-planner/{lecture_id}/source.json"
    uploads_dir = workspace.layout.course_uploads_dir(course_id)
    if uploads_dir.exists() and any(path.is_file() for path in uploads_dir.rglob("*")):
        try:
            return workspace.source_document(
                course_id=course_id,
                lecture_id=lecture_id,
                workspace_path=workspace_path,
            )
        except CanvasWorkspaceError:
            return import_source_bundle_canvas(
                source_root=uploads_dir,
                course_id=course_id,
                lecture_id=lecture_id,
                workspace_path=workspace_path,
            )
    raise SourceBundleCanvasError("Upload course materials before generating a canvas draft.")

from __future__ import annotations

from fastapi import FastAPI

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_schedule_store import read_course_workspace
from lecturepilot.course_source_partition import select_lecture_source_files
from lecturepilot.source_index import indexed_course_files
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError, import_source_bundle_canvas


def course_builder_source_document(app: FastAPI, course_id: str, lecture_id: str) -> CanvasDocument:
    workspace = app.state.canvas_workspace
    workspace_path = f"course-planner/{lecture_id}/source.json"
    uploads_dir = workspace.layout.course_uploads_dir(course_id)
    if uploads_dir.exists() and any(path.is_file() for path in uploads_dir.rglob("*")):
        indexed = indexed_course_files(layout=workspace.layout, course_id=course_id)
        course_workspace = read_course_workspace(workspace.course_media_root(course_id), course_id)
        selected = select_lecture_source_files(
            files=indexed,
            lectures=course_workspace.lectures if course_workspace else [],
            lecture_id=lecture_id,
        )
        if not selected:
            raise SourceBundleCanvasError(
                f"No uploaded source material is assigned to {course_id}/{lecture_id}."
            )
        return import_source_bundle_canvas(
            source_root=uploads_dir,
            course_id=course_id,
            lecture_id=lecture_id,
            workspace_path=workspace_path,
            files=selected,
            derived_root=workspace.layout.course_normalized_dir(course_id),
        )
    raise SourceBundleCanvasError("Upload course materials before generating a canvas draft.")

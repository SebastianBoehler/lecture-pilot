from __future__ import annotations

from fastapi import FastAPI

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_schedule_store import read_course_workspace
from lecturepilot.course_source_partition import select_lecture_source_files
from lecturepilot.lecture_source_manifest import (
    read_lecture_source_manifest,
    write_lecture_source_manifest,
)
from lecturepilot.source_index import refresh_course_source_index
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError, import_source_bundle_canvas
from lecturepilot.workspace_fs import WorkspaceFSError


def course_builder_source_document(app: FastAPI, course_id: str, lecture_id: str) -> CanvasDocument:
    workspace = app.state.canvas_workspace
    workspace_path = f"course-planner/{lecture_id}/source.json"
    uploads_dir = workspace.layout.course_uploads_dir(course_id)
    try:
        source_index = refresh_course_source_index(
            course_id=course_id,
            uploads_dir=uploads_dir,
            index_path=workspace.layout.course_source_index_path(course_id),
        )
        indexed = [item.as_bundle_file() for item in source_index.files]
    except WorkspaceFSError as exc:
        raise SourceBundleCanvasError("Course source contains an unsafe symbolic link.") from exc
    if indexed:
        course_workspace = read_course_workspace(workspace.course_media_root(course_id), course_id)
        selected = select_lecture_source_files(
            files=indexed,
            lectures=course_workspace.lectures if course_workspace else [],
            lecture_id=lecture_id,
        )
        manifest_path = workspace.layout.lecture_source_manifest_path(course_id, lecture_id)
        manifest = read_lecture_source_manifest(manifest_path, course_id, lecture_id)
        explicit_paths = {item.path for item in manifest.files}
        selected_paths = {item.path for item in selected} | explicit_paths
        selected = [item for item in indexed if item.path in selected_paths]
        if not selected:
            raise SourceBundleCanvasError(
                f"No uploaded source material is assigned to {course_id}/{lecture_id}."
            )
        document = import_source_bundle_canvas(
            source_root=uploads_dir,
            course_id=course_id,
            lecture_id=lecture_id,
            workspace_path=workspace_path,
            files=selected,
            derived_root=workspace.layout.course_normalized_dir(course_id),
        )
        write_lecture_source_manifest(
            manifest_path,
            course_id=course_id,
            lecture_id=lecture_id,
            file_paths=[item.path for item in selected],
            source_index=source_index,
        )
        return document
    raise SourceBundleCanvasError("Upload course materials before generating a canvas draft.")

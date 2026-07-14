from __future__ import annotations

import json
import logging
from pathlib import Path
from fastapi import FastAPI

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.compiled_slide_canvas import latex_preview_warning
from lecturepilot.course_schedule_store import read_course_workspace
from lecturepilot.course_source_partition import select_lecture_source_files
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.latex_compilation_client import LatexCompilationError, compile_latex_deck
from lecturepilot.latex_dependency_bundle import resolve_latex_compiler_inputs
from lecturepilot.lecture_slide_source import resolve_lecture_slide_source
from lecturepilot.lecture_source_manifest import (
    read_lecture_source_manifest,
    write_lecture_source_manifest,
)
from lecturepilot.logging_observability import current_operation_id
from lecturepilot.source_index import refresh_course_source_index
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError, import_source_bundle_canvas
from lecturepilot.source_index_models import IndexedSourceFile
from lecturepilot.workspace_fs import WorkspaceFSError


logger = logging.getLogger("uvicorn.error.lecturepilot.compilation")


def course_builder_source_document(app: FastAPI, course_id: str, lecture_id: str) -> CanvasDocument:
    course_root = app.state.canvas_workspace.course_media_root(course_id)
    with locked_course_state(course_root):
        return _course_builder_source_document_locked(app, course_id, lecture_id)


def _course_builder_source_document_locked(
    app: FastAPI, course_id: str, lecture_id: str
) -> CanvasDocument:
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
        lectures = course_workspace.lectures if course_workspace else []
        scheduled = next((item for item in lectures if item.id == lecture_id), None)
        selected = select_lecture_source_files(
            files=indexed,
            lectures=lectures,
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
        slide_source = resolve_lecture_slide_source(
            files=selected,
            material_path=scheduled.material_path if scheduled else None,
            lecture_id=lecture_id,
            preferred_pdf_paths=explicit_paths,
        )
        normalized = workspace.layout.course_normalized_dir(course_id)
        compiler_inputs = (
            resolve_latex_compiler_inputs(
                source_root=uploads_dir,
                source_index=source_index,
                source_path=slide_source.primary_tex_path or "",
                forbidden_paths={
                    item.material_path
                    for item in lectures
                    if item.id != lecture_id and item.material_path
                },
            )
            if slide_source.primary_tex_path and not slide_source.uploaded_pdf_path
            else []
        )
        compiled_pdf, warnings = _compile_slide_preview(
            course_id=course_id,
            lecture_id=lecture_id,
            source_root=uploads_dir,
            compiler_inputs=compiler_inputs,
            source_path=slide_source.primary_tex_path,
            uploaded_pdf_path=slide_source.uploaded_pdf_path,
            output_root=normalized,
        )
        document = import_source_bundle_canvas(
            source_root=uploads_dir,
            course_id=course_id,
            lecture_id=lecture_id,
            workspace_path=workspace_path,
            files=selected,
            derived_root=normalized,
            compiled_slide_pdf=compiled_pdf,
            compiled_slide_source_ref=slide_source.primary_tex_path,
            warnings=warnings,
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


def _compile_slide_preview(
    *,
    course_id: str,
    lecture_id: str,
    source_root: Path,
    compiler_inputs: list[IndexedSourceFile],
    source_path: str | None,
    uploaded_pdf_path: str | None,
    output_root: Path,
) -> tuple[Path | None, list[str]]:
    if not source_path or uploaded_pdf_path:
        return None, []
    try:
        return (
            compile_latex_deck(
                source_root=source_root,
                inputs=compiler_inputs,
                source_path=source_path,
                output_root=output_root,
                lecture_id=lecture_id,
            ),
            [],
        )
    except (LatexCompilationError, OSError) as exc:
        payload = {
            "event": "latex_compilation_failed",
            "course_id": course_id,
            "lecture_id": lecture_id,
            "operation_id": current_operation_id(),
            "error_type": type(exc).__name__,
        }
        if isinstance(exc, LatexCompilationError):
            payload["error_code"] = exc.code
            if exc.request_id:
                payload["compiler_request_id"] = exc.request_id
        logger.warning(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        return None, [latex_preview_warning(lecture_id, source_path)]

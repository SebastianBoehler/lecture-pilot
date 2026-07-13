from __future__ import annotations

from collections import defaultdict
import os
from pathlib import Path
import shutil
import tempfile

from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.course_source_partition import select_lecture_source_files
from lecturepilot.course_update import CourseUpdateError, require_workspace
from lecturepilot.course_update_analysis import analyze_course_update, live_source_index
from lecturepilot.course_update_models import CourseUpdateApplyInput, CourseUpdateApplyResult
from lecturepilot.course_update_storage import staged_file_transaction
from lecturepilot.course_workspace import resolve_course_workspace
from lecturepilot.lecture_source_manifest import (
    read_lecture_source_manifest,
    write_lecture_source_manifest,
)
from lecturepilot.models import CourseWorkspaceSetupInput, LectureScheduleItem
from lecturepilot.storage_layout import StorageLayout


def apply_course_update(
    layout: StorageLayout,
    course_id: str,
    update_id: str,
    payload: CourseUpdateApplyInput,
) -> CourseUpdateApplyResult:
    analysis = analyze_course_update(layout, course_id, update_id)
    workspace = require_workspace(layout, course_id)
    allowed_paths = {
        *[item.path for item in analysis.unassigned_files],
        *[path for candidate in analysis.candidates for path in candidate.file_paths],
    }
    selected_paths = sorted({path for item in payload.lectures for path in item.file_paths})
    if any(path not in allowed_paths for path in selected_paths):
        raise CourseUpdateError("The selected files do not match the current staged update.")

    lectures_by_id = {lecture.id: lecture for lecture in workspace.lectures}
    updated = dict(lectures_by_id)
    affected: list[str] = []
    paths_by_lecture: dict[str, set[str]] = defaultdict(set)
    for selection in payload.lectures:
        lecture = _selected_lecture(workspace, lectures_by_id, updated, selection)
        updated[lecture.id] = lecture
        affected.append(lecture.id)
        paths_by_lecture[lecture.id].update(selection.file_paths)

    final_workspace = workspace.model_copy(
        update={
            "lectures": [
                *(updated[item.id] for item in workspace.lectures),
                *(item for key, item in updated.items() if key not in lectures_by_id),
            ]
        }
    )
    _promote_update(
        layout=layout,
        course_id=course_id,
        update_id=update_id,
        workspace=workspace,
        final_workspace=final_workspace,
        selected_paths=selected_paths,
        paths_by_lecture=paths_by_lecture,
    )
    shutil.rmtree(layout.course_update_root(course_id, update_id), ignore_errors=True)
    return CourseUpdateApplyResult(
        course_id=course_id,
        update_id=update_id,
        applied_files=len(selected_paths),
        affected_lecture_ids=list(dict.fromkeys(affected)),
        workspace=final_workspace,
    )


def _selected_lecture(workspace, existing, updated, selection):
    if selection.lecture_id:
        lecture = existing.get(selection.lecture_id)
        if lecture is None:
            raise CourseUpdateError("An existing lecture selection is invalid.")
        return lecture.model_copy(update={"title": selection.title.strip(), "date": selection.date})
    setup = CourseWorkspaceSetupInput(
        course_title=workspace.course.title,
        target="full-course",
        lectures=[
            LectureScheduleItem(
                number=selection.number,
                title=selection.title,
                date=selection.date,
                material_path=selection.file_paths[0],
            )
        ],
    )
    lecture = resolve_course_workspace(
        setup,
        professor=workspace.course.professor,
        term=workspace.course.term,
        course=workspace.course,
    ).lectures[0]
    if lecture.id in updated:
        raise CourseUpdateError("The new lecture number already exists in this course.")
    return lecture


def _promote_update(
    *, layout, course_id, update_id, workspace, final_workspace, selected_paths, paths_by_lecture
):
    live_index = live_source_index(layout, course_id)
    bundle_files = [item.as_bundle_file() for item in live_index.files]
    manifest_paths = {}
    for lecture_id, selected in paths_by_lecture.items():
        manifest = read_lecture_source_manifest(
            layout.lecture_source_manifest_path(course_id, lecture_id), course_id, lecture_id
        )
        inferred = select_lecture_source_files(
            files=bundle_files, lectures=workspace.lectures, lecture_id=lecture_id
        )
        manifest_paths[lecture_id] = (
            {item.path for item in manifest.files} | {item.path for item in inferred} | selected
        )
    metadata = [
        layout.course_source_index_path(course_id),
        layout.course_root(course_id) / "builder" / "course-workspace.json",
        *(layout.lecture_source_manifest_path(course_id, item) for item in paths_by_lecture),
    ]
    snapshots = {path: path.read_bytes() if path.exists() else None for path in metadata}
    try:
        with staged_file_transaction(
            staged_root=layout.course_update_uploads_dir(course_id, update_id),
            live_root=layout.course_uploads_dir(course_id),
            backup_root=layout.course_update_root(course_id, update_id) / "backup",
            paths=selected_paths,
        ):
            updated_index = live_source_index(layout, course_id)
            write_course_workspace(
                layout.course_root(course_id), final_workspace, replace_lectures=True
            )
            for lecture_id, paths in manifest_paths.items():
                write_lecture_source_manifest(
                    layout.lecture_source_manifest_path(course_id, lecture_id),
                    course_id=course_id,
                    lecture_id=lecture_id,
                    file_paths=list(paths),
                    source_index=updated_index,
                )
    except BaseException:
        _restore(snapshots)
        raise


def _restore(snapshots: dict[Path, bytes | None]) -> None:
    for path, content in snapshots.items():
        if content is None:
            path.unlink(missing_ok=True)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".course-update-restore-", dir=path.parent)
        temporary_path = Path(temporary)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            temporary_path.replace(path)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise

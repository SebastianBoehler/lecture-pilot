from __future__ import annotations

from collections import defaultdict

from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.course_source_partition import select_lecture_source_files
from lecturepilot.course_update import (
    CourseUpdateError,
    begin_course_update_apply,
    finish_course_update_apply,
    mark_course_update_committed,
    require_workspace,
)
from lecturepilot.course_update_analysis import analyze_course_update, live_source_index
from lecturepilot.course_update_models import CourseUpdateApplyInput, CourseUpdateApplyResult
from lecturepilot.course_update_storage import (
    CourseUpdateRecoveryError,
    staged_file_transaction,
)
from lecturepilot.course_update_recovery import (
    locked_course_state,
    retire_committed_course_update,
)
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
    with locked_course_state(layout.course_root(course_id)):
        marker = begin_course_update_apply(layout, course_id, update_id)
        try:
            return _apply_course_update_locked(layout, course_id, update_id, payload)
        except CourseUpdateRecoveryError:
            raise
        except BaseException:
            finish_course_update_apply(marker)
            raise


def _apply_course_update_locked(
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
    retire_committed_course_update(layout.course_update_root(course_id, update_id))
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
    course_root = layout.course_root(course_id)
    with staged_file_transaction(
        staged_root=layout.course_update_uploads_dir(course_id, update_id),
        live_root=layout.course_uploads_dir(course_id),
        backup_root=layout.course_update_root(course_id, update_id) / "recovery",
        paths=selected_paths,
        cleanup_on_success=False,
    ) as transaction:
        for path in metadata:
            transaction.track_file(path, path.relative_to(course_root).as_posix())
        transaction.checkpoint()
        updated_index = live_source_index(layout, course_id)
        write_course_workspace(course_root, final_workspace, replace_lectures=True)
        for lecture_id, paths in manifest_paths.items():
            write_lecture_source_manifest(
                layout.lecture_source_manifest_path(course_id, lecture_id),
                course_id=course_id,
                lecture_id=lecture_id,
                file_paths=list(paths),
                source_index=updated_index,
            )
        mark_course_update_committed(layout.course_update_root(course_id, update_id) / ".applying")

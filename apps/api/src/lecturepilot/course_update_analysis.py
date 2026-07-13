from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
import re

from lecturepilot.course_update import require_update_root, require_workspace
from lecturepilot.course_update_models import (
    CourseUpdateAnalysis,
    CourseUpdateFileChange,
    CourseUpdateLectureCandidate,
    CourseUpdateLectureOption,
)
from lecturepilot.lecture_schedule import LECTURE_FILE_RE, propose_lecture_schedule
from lecturepilot.lecture_source_manifest import read_lecture_source_manifest
from lecturepilot.source_bundle import SourceBundleFile
from lecturepilot.source_index import refresh_course_source_index
from lecturepilot.source_index_models import CourseSourceIndex
from lecturepilot.storage_layout import StorageLayout


def analyze_course_update(
    layout: StorageLayout, course_id: str, update_id: str
) -> CourseUpdateAnalysis:
    workspace = require_workspace(layout, course_id)
    root = require_update_root(layout, course_id, update_id)
    staged = refresh_course_source_index(
        course_id=course_id,
        uploads_dir=root / "uploads",
        index_path=root / "source-index.json",
    )
    changes, unchanged = _changes(staged, live_source_index(layout, course_id))
    assignments = _assignments(layout, course_id, workspace, changes)
    candidates = _candidates(
        course_id=course_id,
        workspace=workspace,
        changes=changes,
        assignments=assignments,
        staged_root=root / "uploads",
    )
    assigned_paths = {path for paths in assignments.values() for path in paths}
    return CourseUpdateAnalysis(
        course_id=course_id,
        update_id=update_id,
        candidates=candidates,
        existing_lectures=[
            CourseUpdateLectureOption(
                lecture_id=lecture.id,
                number=lecture_number(lecture.id, index),
                title=lecture.title,
                date=lecture.date,
            )
            for index, lecture in enumerate(workspace.lectures, start=1)
        ],
        unassigned_files=[item for item in changes if item.path not in assigned_paths],
        unchanged_files=unchanged,
    )


def live_source_index(layout: StorageLayout, course_id: str) -> CourseSourceIndex:
    return refresh_course_source_index(
        course_id=course_id,
        uploads_dir=layout.course_uploads_dir(course_id),
        index_path=layout.course_source_index_path(course_id),
    )


def _changes(
    staged: CourseSourceIndex, live: CourseSourceIndex
) -> tuple[list[CourseUpdateFileChange], int]:
    existing = {item.path: item for item in live.files}
    changes = []
    unchanged = 0
    for item in staged.files:
        previous = existing.get(item.path)
        if previous and previous.sha256 == item.sha256:
            unchanged += 1
            continue
        changes.append(
            CourseUpdateFileChange(
                path=item.path,
                kind=item.kind,
                size_bytes=item.size_bytes,
                sha256=item.sha256,
                status="changed" if previous else "new",
            )
        )
    return changes, unchanged


def _assignments(layout, course_id, workspace, changes):
    paths_to_ids: dict[str, set[str]] = defaultdict(set)
    numbers = {_numeric(lecture.id): lecture.id for lecture in workspace.lectures}
    for lecture in workspace.lectures:
        manifest = read_lecture_source_manifest(
            layout.lecture_source_manifest_path(course_id, lecture.id), course_id, lecture.id
        )
        for item in manifest.files:
            paths_to_ids[item.path].add(lecture.id)
    assigned: dict[str, list[str]] = defaultdict(list)
    for item in changes:
        manifest_ids = paths_to_ids.get(item.path, set())
        if len(manifest_ids) == 1:
            assigned[next(iter(manifest_ids))].append(item.path)
            continue
        match = LECTURE_FILE_RE.search(item.path)
        if match:
            number = int(match.group(1))
            assigned[numbers.get(number, f"new:{number}")].append(item.path)
    return assigned


def _candidates(*, course_id, workspace, changes, assignments, staged_root):
    existing = {lecture.id: lecture for lecture in workspace.lectures}
    candidates = []
    for lecture_id, paths in assignments.items():
        if lecture_id not in existing:
            continue
        lecture = existing[lecture_id]
        candidates.append(
            CourseUpdateLectureCandidate(
                candidate_id=f"update:{lecture.id}",
                action="update",
                lecture_id=lecture.id,
                number=lecture_number(lecture.id, 1),
                title=lecture.title,
                date=lecture.date,
                file_paths=sorted(paths),
            )
        )
    new_groups = {
        int(key.split(":", 1)[1]): paths
        for key, paths in assignments.items()
        if key.startswith("new:")
    }
    if not new_groups:
        return candidates
    by_path = {item.path: item for item in changes}
    first_date = max(item.date for item in workspace.lectures) + timedelta(days=7)
    proposal = propose_lecture_schedule(
        course_id=course_id,
        files=[
            SourceBundleFile(
                path=path,
                kind=by_path[path].kind,
                size_bytes=by_path[path].size_bytes,
            )
            for paths in new_groups.values()
            for path in paths
        ],
        roots=[staged_root],
        first_lecture_date=first_date,
    )
    proposed = {int(item.number): item for item in proposal.lectures}
    for number, paths in sorted(new_groups.items()):
        item = proposed.get(number)
        candidates.append(
            CourseUpdateLectureCandidate(
                candidate_id=f"new:{number}",
                action="new",
                number=f"{number:02d}",
                title=item.title if item else f"Lecture {number:02d}",
                date=item.date if item else first_date,
                file_paths=sorted(paths),
            )
        )
    return candidates


def _numeric(value: str) -> int | None:
    match = re.search(r"(\d+)$", value)
    return int(match.group(1)) if match else None


def lecture_number(value: str, fallback: int) -> str:
    number = _numeric(value)
    return f"{number:02d}" if number is not None else f"{fallback:02d}"

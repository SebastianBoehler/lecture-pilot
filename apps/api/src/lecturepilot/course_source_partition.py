from __future__ import annotations

import re
from collections import Counter
from pathlib import PurePosixPath

from lecturepilot.lecture_schedule import LECTURE_FILE_RE
from lecturepilot.models import Lecture
from lecturepilot.source_bundle import SourceBundleFile


COURSE_WIDE_RE = re.compile(
    r"(?:^|[/_-])(syllabus|readme|module[-_ ]?handbook|course[-_ ]?(outline|overview|schedule))(?:\D|$)",
    re.IGNORECASE,
)


def select_lecture_source_files(
    *,
    files: list[SourceBundleFile],
    lectures: list[Lecture],
    lecture_id: str,
) -> list[SourceBundleFile]:
    if not lectures or len(lectures) == 1:
        return files
    target = next((lecture for lecture in lectures if lecture.id == lecture_id), None)
    if target is None:
        return []

    selected: set[str] = set()
    assigned_path = _path(target.material_path)
    if assigned_path:
        selected.add(assigned_path.as_posix())
        parent = assigned_path.parent
        if _is_unique_material_parent(parent, lectures):
            selected.update(item.path for item in files if _is_within(_path(item.path), parent))

    target_number = _lecture_number(lecture_id)
    if target_number is not None:
        selected.update(item.path for item in files if _lecture_number(item.path) == target_number)
    selected.update(item.path for item in files if COURSE_WIDE_RE.search(item.path))
    selected.update(_metadata_sidecars(files, selected))
    return [item for item in files if item.path in selected]


def _is_unique_material_parent(parent: PurePosixPath, lectures: list[Lecture]) -> bool:
    if str(parent) == ".":
        return False
    parents = Counter(
        _path(lecture.material_path).parent
        for lecture in lectures
        if _path(lecture.material_path) is not None
    )
    return parents[parent] == 1


def _metadata_sidecars(files: list[SourceBundleFile], selected: set[str]) -> set[str]:
    candidates = set()
    for path in selected:
        source = PurePosixPath(path)
        candidates.add(f"{path}.json")
        candidates.add(source.with_suffix(".json").as_posix())
    return {item.path for item in files if item.path in candidates}


def _lecture_number(value: str) -> int | None:
    match = LECTURE_FILE_RE.search(value)
    return int(match.group(1)) if match else None


def _is_within(path: PurePosixPath | None, parent: PurePosixPath) -> bool:
    return path is not None and path != parent and parent in path.parents


def _path(value: str | None) -> PurePosixPath | None:
    return PurePosixPath(value) if value else None

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from lecturepilot.core.durable_files import atomic_write_text
from lecturepilot.sources.source_index_models import CourseSourceIndex


class LectureSourceFile(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class LectureSourceManifest(BaseModel):
    course_id: str
    lecture_id: str
    files: list[LectureSourceFile] = Field(default_factory=list, max_length=500)


def read_lecture_source_manifest(
    path: Path, course_id: str, lecture_id: str
) -> LectureSourceManifest:
    if not path.exists():
        return LectureSourceManifest(course_id=course_id, lecture_id=lecture_id)
    try:
        manifest = LectureSourceManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return LectureSourceManifest(course_id=course_id, lecture_id=lecture_id)
    if manifest.course_id != course_id or manifest.lecture_id != lecture_id:
        return LectureSourceManifest(course_id=course_id, lecture_id=lecture_id)
    return manifest


def write_lecture_source_manifest(
    path: Path,
    *,
    course_id: str,
    lecture_id: str,
    file_paths: list[str],
    source_index: CourseSourceIndex,
) -> LectureSourceManifest:
    indexed = {item.path: item.sha256 for item in source_index.files}
    manifest = LectureSourceManifest(
        course_id=course_id,
        lecture_id=lecture_id,
        files=[
            LectureSourceFile(path=file_path, sha256=indexed[file_path])
            for file_path in sorted(set(file_paths))
            if file_path in indexed
        ],
    )
    atomic_write_text(path, manifest.model_dump_json(indent=2))
    return manifest

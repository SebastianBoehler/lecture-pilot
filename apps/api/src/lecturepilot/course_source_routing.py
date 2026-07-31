from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from lecturepilot.course_source_partition import (
    is_course_wide_source,
    select_lecture_source_files,
)
from lecturepilot.course_source_routing_models import (
    CourseSourceRoute,
    CourseSourceRoutingInput,
    CourseSourceRoutingManifest,
    SourceRouteRole,
)
from lecturepilot.durable_files import ensure_durable_directory, fsync_directory
from lecturepilot.models import Lecture
from lecturepilot.lecture_schedule import LECTURE_FILE_RE
from lecturepilot.source_index_models import CourseSourceIndex, IndexedSourceFile


class SourceRoutingError(ValueError):
    pass


class StaleSourceRoutingError(SourceRoutingError):
    pass


def source_revision(index: CourseSourceIndex, lectures: list[Lecture]) -> str:
    digest = hashlib.sha256()
    for item in sorted(index.files, key=lambda candidate: candidate.path):
        digest.update(f"{item.path}\0{item.sha256}\n".encode())
    for lecture in sorted(lectures, key=lambda candidate: candidate.id):
        digest.update(
            (
                f"{lecture.id}\0{lecture.title}\0{lecture.date.isoformat()}\0"
                f"{lecture.material_path or ''}\n"
            ).encode()
        )
    return digest.hexdigest()


def review_source_routing(
    *,
    course_id: str,
    index: CourseSourceIndex,
    lectures: list[Lecture],
    routing_path: Path,
) -> CourseSourceRoutingManifest:
    revision = source_revision(index, lectures)
    stored = read_source_routing(routing_path, course_id)
    if stored is not None and stored.source_revision == revision:
        return stored
    return CourseSourceRoutingManifest(
        course_id=course_id,
        source_revision=revision,
        confirmed=False,
        routes=_suggest_routes(index.files, lectures),
    )


def confirm_source_routing(
    *,
    course_id: str,
    index: CourseSourceIndex,
    lectures: list[Lecture],
    routing_path: Path,
    routing: CourseSourceRoutingInput,
) -> CourseSourceRoutingManifest:
    current_revision = source_revision(index, lectures)
    if routing.source_revision != current_revision:
        raise StaleSourceRoutingError(
            "Uploaded course sources changed. Review the refreshed routing before confirming."
        )
    indexed_by_path = {item.path: item for item in index.files}
    routes_by_path = {item.path: item for item in routing.routes}
    if (
        len(routes_by_path) != len(routing.routes)
        or routes_by_path.keys() != indexed_by_path.keys()
    ):
        raise SourceRoutingError("Assign every uploaded source exactly once before confirming.")

    lecture_ids = {lecture.id for lecture in lectures}
    for path, route in routes_by_path.items():
        indexed = indexed_by_path[path]
        if route.kind != indexed.kind or route.sha256 != indexed.sha256:
            raise StaleSourceRoutingError(
                "Uploaded course sources changed. Review the refreshed routing before confirming."
            )
        if route.lecture_id is not None and route.lecture_id not in lecture_ids:
            raise SourceRoutingError(f"Unknown lecture assignment for {path}.")

    manifest = CourseSourceRoutingManifest(
        course_id=course_id,
        source_revision=current_revision,
        confirmed=True,
        routes=routing.routes,
    )
    _write_source_routing(routing_path, manifest)
    return manifest


def selected_routed_files(
    *,
    course_id: str,
    lecture_id: str,
    index: CourseSourceIndex,
    lectures: list[Lecture],
    routing_path: Path,
) -> list[IndexedSourceFile]:
    routing = read_source_routing(routing_path, course_id)
    if (
        routing is None
        or not routing.confirmed
        or routing.source_revision != source_revision(index, lectures)
    ):
        raise SourceRoutingError(
            "Review and confirm source routing before generating canvas drafts."
        )
    included = {
        route.path
        for route in routing.routes
        if route.role == SourceRouteRole.COURSE_WIDE
        or (route.role == SourceRouteRole.LECTURE and route.lecture_id == lecture_id)
    }
    return [item for item in index.files if item.path in included]


def read_source_routing(path: Path, course_id: str) -> CourseSourceRoutingManifest | None:
    if not path.exists():
        return None
    try:
        routing = CourseSourceRoutingManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None
    return routing if routing.course_id == course_id else None


def _suggest_routes(
    files: list[IndexedSourceFile], lectures: list[Lecture]
) -> list[CourseSourceRoute]:
    bundle_files = [item.as_bundle_file() for item in files]
    selected_by_lecture = {
        lecture.id: _suggested_lecture_paths(bundle_files, lectures, lecture)
        for lecture in lectures
    }
    routes = []
    for item in files:
        lecture_ids = [
            lecture.id for lecture in lectures if item.path in selected_by_lecture[lecture.id]
        ]
        role = SourceRouteRole.REFERENCE_ONLY
        lecture_id = None
        if is_course_wide_source(item.path):
            role = SourceRouteRole.COURSE_WIDE
        elif len(lecture_ids) == 1:
            role = SourceRouteRole.LECTURE
            lecture_id = lecture_ids[0]
        routes.append(
            CourseSourceRoute(
                path=item.path,
                kind=item.kind,
                sha256=item.sha256,
                role=role,
                lecture_id=lecture_id,
            )
        )
    return routes


def _suggested_lecture_paths(files, lectures: list[Lecture], lecture: Lecture) -> set[str]:
    if len(lectures) > 1:
        return {
            item.path
            for item in select_lecture_source_files(
                files=files,
                lectures=lectures,
                lecture_id=lecture.id,
            )
        }
    material_path = lecture.material_path
    number_match = LECTURE_FILE_RE.search(lecture.id)
    number = int(number_match.group(1)) if number_match else None
    return {
        item.path
        for item in files
        if item.path == material_path
        or (
            number is not None
            and (match := LECTURE_FILE_RE.search(item.path)) is not None
            and int(match.group(1)) == number
        )
    }


def _write_source_routing(path: Path, routing: CourseSourceRoutingManifest) -> None:
    ensure_durable_directory(path.parent)
    descriptor, temporary = tempfile.mkstemp(prefix=".source-routing-", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(routing.model_dump_json(indent=2))
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
        fsync_directory(path.parent)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise

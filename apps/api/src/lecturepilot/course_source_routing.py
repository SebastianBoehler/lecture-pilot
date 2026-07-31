from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from lecturepilot.course_source_routing_models import (
    CourseSourceRoute,
    CourseSourceRoutingInput,
    CourseSourceRoutingManifest,
    SourceRouteRole,
)
from lecturepilot.durable_files import ensure_durable_directory, fsync_directory
from lecturepilot.models import Lecture
from lecturepilot.source_index_models import CourseSourceIndex, IndexedSourceFile


class SourceRoutingError(ValueError):
    pass


class StaleSourceRoutingError(SourceRoutingError):
    pass


class SourceRoutingProposalRequired(SourceRoutingError):
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
    raise SourceRoutingProposalRequired(
        "Generate an agent source-assignment proposal before reviewing it."
    )


def save_source_routing_proposal(
    *,
    course_id: str,
    index: CourseSourceIndex,
    lectures: list[Lecture],
    routing_path: Path,
    routes: list[CourseSourceRoute],
) -> CourseSourceRoutingManifest:
    indexed_paths = {item.path for item in index.files}
    route_paths = {route.path for route in routes}
    if len(route_paths) != len(routes) or route_paths != indexed_paths:
        raise SourceRoutingError(
            "The routing agent must assign every uploaded source exactly once."
        )
    manifest = CourseSourceRoutingManifest(
        course_id=course_id,
        source_revision=source_revision(index, lectures),
        confirmed=False,
        routes=routes,
    )
    _write_source_routing(routing_path, manifest)
    return manifest


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

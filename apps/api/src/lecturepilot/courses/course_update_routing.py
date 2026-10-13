"""Source routing written by an applied course update, without a routing model call.

The update review already assigns every applied file: to one lecture (lecture-specific),
to several or all existing lectures (course-wide) or not at all (ignored files are never
applied). When the course's routing was confirmed for the sources before the update, those
assignments extend it: existing routes are kept, applied files get their reviewed route and
the routing is confirmed for the updated sources through the ordinary confirmation. Applied
routes never exclude a file and the previous confirmation already pruned unused uploads, so
nothing is pruned. Without a current confirmed routing the professor confirms as usual.
"""

from __future__ import annotations

from lecturepilot.core.models import Lecture
from lecturepilot.sources.course_source_routing import read_source_routing, source_revision
from lecturepilot.sources.course_source_routing_models import (
    CourseSourceRoute,
    CourseSourceRoutingInput,
    CourseSourceRoutingManifest,
    SourceRouteRole,
)
from lecturepilot.sources.source_index_models import CourseSourceIndex


def confirmed_routing(
    layout, course_id: str, index: CourseSourceIndex, lectures: list[Lecture]
) -> CourseSourceRoutingManifest | None:
    """The stored routing if it is confirmed for exactly these sources and lectures."""
    routing = read_source_routing(layout.course_source_routing_path(course_id), course_id)
    if (
        routing is None
        or not routing.confirmed
        or routing.source_revision != source_revision(index, lectures)
    ):
        return None
    return routing


def updated_routing(
    *,
    previous: CourseSourceRoutingManifest,
    previous_lecture_ids: set[str],
    index: CourseSourceIndex,
    lectures: list[Lecture],
    paths_by_lecture: dict[str, set[str]],
) -> CourseSourceRoutingInput | None:
    """Return the confirmable routing after the update, or None when it needs review."""
    owners: dict[str, set[str]] = {}
    for lecture_id, paths in paths_by_lecture.items():
        for path in paths:
            owners.setdefault(path, set()).add(lecture_id)
    existing = {route.path: route for route in previous.routes}
    routes = []
    for item in index.files:
        route = existing.get(item.path)
        if item.path in owners:
            role, lecture_id = _reviewed_role(owners[item.path], route, previous_lecture_ids)
        elif route is not None:
            role, lecture_id = route.role, route.lecture_id
        else:
            return None  # An unrouted file outside this update: the professor reviews it.
        if route is not None and route.sha256 != item.sha256:
            route = None  # Changed content: its processing status is derived again.
        routes.append(
            CourseSourceRoute(
                path=item.path,
                kind=item.kind,
                sha256=item.sha256,
                role=role,
                lecture_id=lecture_id,
                **({"processing_status": route.processing_status} if route else {}),
            )
        )
    return CourseSourceRoutingInput(source_revision=source_revision(index, lectures), routes=routes)


def lecture_paths(routing: CourseSourceRoutingInput, lecture_id: str) -> list[str]:
    return [
        route.path
        for route in routing.routes
        if route.role == SourceRouteRole.COURSE_WIDE
        or (route.role == SourceRouteRole.LECTURE and route.lecture_id == lecture_id)
    ]


def _reviewed_role(
    owners: set[str], previous: CourseSourceRoute | None, existing_lectures: set[str]
) -> tuple[SourceRouteRole, str | None]:
    shared = previous is not None and previous.role == SourceRouteRole.COURSE_WIDE
    if len(owners) > 1 or (shared and existing_lectures <= owners):
        return SourceRouteRole.COURSE_WIDE, None
    return SourceRouteRole.LECTURE, next(iter(owners))

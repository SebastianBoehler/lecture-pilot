"""Accept a first source-routing proposal that needs no professor decision.

A proposal is accepted automatically only when it is complete and non-destructive:
every lecture has its own evidence, each scheduled primary file is routed to its
lecture, no source needs OCR, and confirming would delete no upload. Anything else
waits for the professor. Acceptance runs the ordinary confirmation, so pruning,
index and revision updates are identical to a manual confirm; the assignment stays
editable and can be confirmed again. No model call is involved.
"""

from lecturepilot.course_source_cleanup import confirm_and_prune_sources
from lecturepilot.course_source_routing import StaleSourceRoutingError
from lecturepilot.course_source_routing_models import (
    CourseSourceRoutingInput,
    CourseSourceRoutingManifest,
    SourceProcessingStatus,
    SourceRouteRole,
)
from lecturepilot.source_retention import retained_source_paths


def needs_no_review(manifest: CourseSourceRoutingManifest, lectures) -> bool:
    """`manifest` carries the processing status computed outside the course lock."""
    routes = {route.path: route for route in manifest.routes}
    assigned = {
        route.lecture_id for route in manifest.routes if route.role == SourceRouteRole.LECTURE
    }
    return (
        not manifest.confirmed
        and all(r.processing_status != SourceProcessingStatus.OCR_NEEDED for r in routes.values())
        and all(lecture.id in assigned for lecture in lectures)
        and all(
            routes[lecture.material_path].lecture_id == lecture.id
            for lecture in lectures
            if lecture.material_path in routes
        )
    )


def accept_without_review(*, layout, course_id, index, lectures, manifest):
    """Caller holds the course lock. Returns the confirmed manifest, or None to review."""
    keep = retained_source_paths(layout, course_id, index, manifest.routes, lectures)
    if any(item.path not in keep for item in index.files):
        return None  # Confirmation would delete an upload: the professor decides.
    try:
        return confirm_and_prune_sources(
            layout=layout,
            course_id=course_id,
            index=index,
            lectures=lectures,
            routing=CourseSourceRoutingInput(
                source_revision=manifest.source_revision, routes=manifest.routes
            ),
        )
    except StaleSourceRoutingError:
        return None  # Sources changed meanwhile; the professor reviews the refreshed proposal.

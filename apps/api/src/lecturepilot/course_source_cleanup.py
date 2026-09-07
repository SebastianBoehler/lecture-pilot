from __future__ import annotations

from uuid import uuid4

from lecturepilot.course_source_routing import (
    SourceRoutingError,
    StaleSourceRoutingError,
    confirm_source_routing,
    source_revision,
)
from lecturepilot.course_source_routing_models import (
    CourseSourceRoutingInput,
    CourseSourceRoutingManifest,
)
from lecturepilot.models import Lecture
from lecturepilot.source_index_models import CourseSourceIndex
from lecturepilot.storage_layout import StorageLayout
from lecturepilot.course_update import mark_course_update_committed
from lecturepilot.course_update_recovery import retire_committed_course_update
from lecturepilot.course_update_storage import staged_file_transaction
from lecturepilot.durable_files import atomic_write_json, ensure_durable_directory, fsync_directory
from lecturepilot.source_index import refresh_course_source_index
from lecturepilot.source_retention import retained_source_paths
from lecturepilot.source_retention_provenance import (
    retention_provenance_path,
    record_retention_provenance,
)
from lecturepilot.course_canvas_repairs import _course_provenance
from lecturepilot.workspace_fs import WorkspaceFSError


def confirm_and_prune_sources(
    *,
    layout: StorageLayout,
    course_id: str,
    index: CourseSourceIndex,
    lectures: list[Lecture],
    routing: CourseSourceRoutingInput,
) -> CourseSourceRoutingManifest:
    """Caller holds the course lock; existing update recovery protects deletion."""
    course_root = layout.course_root(course_id)
    uploads = layout.course_uploads_dir(course_id)
    routing_path = layout.course_source_routing_path(course_id)
    index_path = layout.course_source_index_path(course_id)
    # Validate the submitted paths against the index before opening any of them.
    if routing.source_revision != source_revision(index, lectures):
        raise StaleSourceRoutingError(
            "Uploaded course sources changed. Review the refreshed routing."
        )
    if {r.path for r in routing.routes} != {f.path for f in index.files}:
        raise SourceRoutingError("Assign every uploaded source exactly once before confirming.")
    keep = retained_source_paths(layout, course_id, index, routing.routes, lectures)
    discarded = [f for f in index.files if f.path not in keep]
    if not discarded:
        return confirm_source_routing(
            course_id=course_id,
            index=index,
            lectures=lectures,
            routing_path=routing_path,
            routing=routing,
        )
    targets = [uploads / f.path for f in discarded]
    retained_hashes = {f.sha256 for f in index.files if f.path in keep}
    normalized = layout.course_normalized_dir(course_id)
    for digest in {f.sha256 for f in discarded} - retained_hashes:
        root = normalized / digest
        if root.is_symlink():
            raise WorkspaceFSError("Normalized source must not be a symbolic link.")
        if root.exists():
            targets.extend(p for p in root.rglob("*") if p.is_file() or p.is_symlink())
    for path in targets:
        if path.is_symlink() or not path.resolve().is_relative_to(course_root.resolve()):
            raise WorkspaceFSError("Source cleanup must remain inside the course workspace.")
    update_root = course_root / "builder" / "updates" / f"source-cleanup-{uuid4()}"
    ensure_durable_directory(update_root)
    marker = update_root / ".applying"
    atomic_write_json(marker, {"operation": "source-cleanup"})
    with staged_file_transaction(
        staged_root=uploads,
        live_root=uploads,
        backup_root=update_root / "recovery",
        paths=[],
        cleanup_on_success=False,
    ) as transaction:
        for path in [routing_path, index_path, retention_provenance_path(course_root), *targets]:
            transaction.track_file(path, path.relative_to(course_root).as_posix())
        transaction.checkpoint()
        confirm_source_routing(
            course_id=course_id,
            index=index,
            lectures=lectures,
            routing_path=routing_path,
            routing=routing,
        )
        previous_provenance = _course_provenance(layout, course_id)
        for path in targets:
            path.unlink()
            fsync_directory(path.parent)
        current = refresh_course_source_index(
            course_id=course_id, uploads_dir=uploads, index_path=index_path
        )
        manifest = confirm_source_routing(
            course_id=course_id,
            index=current,
            lectures=lectures,
            routing_path=routing_path,
            routing=CourseSourceRoutingInput(
                source_revision=source_revision(current, lectures),
                routes=[r for r in routing.routes if r.path in keep],
            ),
        )
        remaining_provenance = _course_provenance(layout, course_id)
        record_retention_provenance(
            course_root,
            previous=previous_provenance,
            remaining=remaining_provenance,
        )
        mark_course_update_committed(marker)
    retire_committed_course_update(update_root)
    return manifest

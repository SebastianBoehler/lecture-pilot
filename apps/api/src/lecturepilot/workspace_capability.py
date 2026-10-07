from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lecturepilot.canvas_workspace import CanvasWorkspace


@dataclass(frozen=True)
class CapabilityRoot:
    logical_path: str
    host_path: Path
    writable: bool = False
    allowed_files: frozenset[str] | None = None
    excluded_names: frozenset[str] = frozenset()
    file_digests: tuple[tuple[str, str], ...] | None = None
    read_guard: Callable[[], AbstractContextManager[None]] | None = None


@dataclass(frozen=True)
class WorkspaceCapability:
    roots: tuple[CapabilityRoot, ...]

    def logical_roots(self) -> list[str]:
        return sorted(root.logical_path for root in self.roots)


def learner_workspace_capability(
    canvas_workspace: CanvasWorkspace,
    *,
    user_id: str,
    course_id: str,
    lecture_id: str,
) -> WorkspaceCapability:
    layout = canvas_workspace.layout
    from lecturepilot.canvas_annotations import AnnotationStore

    annotations = AnnotationStore(layout, user_id, course_id, lecture_id)
    return WorkspaceCapability(
        roots=(
            CapabilityRoot(
                "/lecture/annotations",
                annotations.directory,
                writable=True,
            ),
            CapabilityRoot(
                "/lecture/canvas",
                layout.user_canvas_dir(user_id, course_id, lecture_id),
                writable=True,
            ),
            CapabilityRoot("/user/memories", layout.user_memories_dir(user_id)),
            CapabilityRoot(
                "/user/course/memories",
                layout.user_course_memories_dir(user_id, course_id),
            ),
            CapabilityRoot("/user/profile.json", layout.user_root(user_id) / "profile.json"),
            CapabilityRoot(
                "/course/canvas",
                layout.course_canvas_dir(course_id, lecture_id),
                excluded_names=frozenset({"learning-map.json"}),
            ),
            _learner_source_root(canvas_workspace, course_id, lecture_id),
        )
    )


def course_builder_capability(
    canvas_workspace: CanvasWorkspace,
    *,
    course_id: str,
    lecture_id: str,
) -> WorkspaceCapability:
    layout = canvas_workspace.layout
    return WorkspaceCapability(
        roots=(
            CapabilityRoot("/course/source/uploads", layout.course_uploads_dir(course_id)),
            CapabilityRoot(
                "/course/canvas-draft",
                layout.course_canvas_draft_dir(course_id, lecture_id),
                writable=True,
            ),
        )
    )


def _learner_source_root(
    workspace: CanvasWorkspace, course_id: str, lecture_id: str
) -> CapabilityRoot:
    from lecturepilot.course_update_recovery import locked_course_state
    from lecturepilot.workspace_fs import WorkspaceFSError
    from lecturepilot.source_capability_guard import shared_source_access, source_state_identity

    course_root = workspace.layout.course_root(course_id)
    try:
        with locked_course_state(course_root):
            identity = source_state_identity(workspace.layout, course_id, lecture_id)
            binding = _validated_source_binding(workspace, course_id, lecture_id)
            if identity != source_state_identity(workspace.layout, course_id, lecture_id):
                raise ValueError("Source identity changed during validation.")
    except (OSError, ValueError, RuntimeError):
        binding = None

    @contextmanager
    def guard() -> Iterator[None]:
        if binding is None:
            raise WorkspaceFSError("Published source capability is unavailable or stale.")
        with shared_source_access(
            course_root, workspace.layout.course_canvas_dir(course_id, lecture_id)
        ):
            try:
                current = source_state_identity(workspace.layout, course_id, lecture_id)
            except (OSError, ValueError, RuntimeError) as exc:
                raise WorkspaceFSError(
                    "Published source capability is unavailable or stale."
                ) from exc
            if binding is None or current != identity:
                raise WorkspaceFSError("Published source capability is unavailable or stale.")
            yield

    files = binding[1] if binding is not None else ()
    return CapabilityRoot(
        "/course/source/uploads",
        workspace.layout.course_uploads_dir(course_id),
        allowed_files=frozenset(path for path, _ in files),
        file_digests=files,
        read_guard=guard,
    )


def _validated_source_binding(
    workspace: CanvasWorkspace, course_id: str, lecture_id: str
) -> tuple[str, tuple[tuple[str, str], ...]]:
    from lecturepilot.course_canvas_repairs import lecture_source_revision
    from lecturepilot.course_schedule_store import read_course_workspace
    from lecturepilot.course_source_routing import source_revision
    from lecturepilot.course_source_routing_models import CourseSourceRoutingManifest
    from lecturepilot.lecture_source_manifest import LectureSourceManifest
    from lecturepilot.source_index_models import CourseSourceIndex

    layout = workspace.layout
    manifest = LectureSourceManifest.model_validate_json(
        layout.lecture_source_manifest_path(course_id, lecture_id).read_text(encoding="utf-8")
    )
    routing = CourseSourceRoutingManifest.model_validate_json(
        layout.course_source_routing_path(course_id).read_text(encoding="utf-8")
    )
    index = CourseSourceIndex.model_validate_json(
        layout.course_source_index_path(course_id).read_text(encoding="utf-8")
    )
    course = read_course_workspace(layout.course_root(course_id), course_id)
    if (
        manifest.course_id != course_id
        or manifest.lecture_id != lecture_id
        or not manifest.files
        or routing.course_id != course_id
        or not routing.confirmed
        or index.course_id != course_id
        or index.schema_version != 1
        or course is None
        or routing.source_revision != source_revision(index, course.lectures)
    ):
        raise ValueError("Source confirmation is unavailable or stale.")
    indexed = {item.path: item for item in index.files}
    routed = {item.path: item for item in routing.routes}
    files = tuple(sorted((item.path, item.sha256) for item in manifest.files))
    if (
        len(indexed) != len(index.files)
        or len(routed) != len(routing.routes)
        or indexed.keys() != routed.keys()
        or len(dict(files)) != len(files)
    ):
        raise ValueError("Source assignments are invalid.")
    for path, digest in files:
        item, route = indexed.get(path), routed.get(path)
        if (
            item is None
            or route is None
            or item.sha256 != digest
            or route.sha256 != digest
            or route.kind != item.kind
            or not (
                route.role == "course_wide"
                or (route.role == "lecture" and route.lecture_id == lecture_id)
            )
        ):
            raise ValueError("Lecture source assignments are invalid.")
    snapshot = workspace.course_canvas_store.read_current_published_snapshot(
        course_id=course_id, lecture_id=lecture_id
    )
    revision = lecture_source_revision(layout, course_id=course_id, lecture_id=lecture_id)
    if snapshot is None or revision is None or snapshot.publication.source_revision != revision:
        raise ValueError("Publication source revision is stale.")
    return revision, files

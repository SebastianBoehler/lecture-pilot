from __future__ import annotations

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
    return WorkspaceCapability(
        roots=(
            CapabilityRoot(
                "/lecture/canvas",
                layout.user_canvas_dir(user_id, course_id, lecture_id),
                writable=True,
            ),
            CapabilityRoot("/user/memories", layout.user_memories_dir(user_id), writable=True),
            CapabilityRoot(
                "/user/course/memories",
                layout.user_course_memories_dir(user_id, course_id),
                writable=True,
            ),
            CapabilityRoot("/user/profile.json", layout.user_root(user_id) / "profile.json"),
            CapabilityRoot("/course/canvas", layout.course_canvas_dir(course_id, lecture_id)),
            CapabilityRoot("/course/source/uploads", layout.course_uploads_dir(course_id)),
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

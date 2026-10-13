"""Lecture-local source revisions.

A lecture's source revision depends only on its own schedule entry (id, title, date,
material path), the files selected for it (lecture-specific and course-wide routes, or its
manifest while a course has no routing yet) with their current indexed content hashes, and
the routes of exactly those files. Other lectures, unrelated uploads and unrelated routes do
not change it; a course-wide file changes every lecture that uses it.

Revisions bound before this definition stay valid through a per-lecture alias written once
by ``storage_migration_lecture_source_alias``: while the computed local revision equals the
alias's ``local`` value, the stored ``legacy`` revision is returned. Once the lecture's own
inputs change, the local revision is returned and earlier bindings become stale.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from lecturepilot.core.models import CourseWorkspaceResult, Lecture
from lecturepilot.core.storage_layout import StorageLayout
from lecturepilot.sources.course_source_routing import read_source_routing
from lecturepilot.sources.course_source_routing_models import (
    CourseSourceRoute,
    CourseSourceRoutingManifest,
    SourceRouteRole,
)
from lecturepilot.sources.lecture_source_manifest import read_lecture_source_manifest
from lecturepilot.sources.source_index_models import CourseSourceIndex

_REVISION = r"^[a-f0-9]{64}$"


class LectureSourceAlias(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    local: str = Field(pattern=_REVISION)
    legacy: str = Field(pattern=_REVISION)


@dataclass(frozen=True)
class CourseSourceInputs:
    """One read of the course-level files every lecture revision is selected from."""

    layout: StorageLayout
    course_id: str
    lectures: dict[str, Lecture]
    indexed: dict[str, str] | None
    routing: CourseSourceRoutingManifest | None

    @classmethod
    def load(cls, layout: StorageLayout, course_id: str) -> CourseSourceInputs:
        return cls(
            layout=layout,
            course_id=course_id,
            lectures={item.id: item for item in _read_lectures(layout, course_id)},
            indexed=_read_index(layout.course_source_index_path(course_id), course_id),
            routing=read_source_routing(layout.course_source_routing_path(course_id), course_id),
        )

    def local_revision(self, lecture_id: str) -> str | None:
        files = self._selected_files(lecture_id)
        if not files:
            return None
        lecture = self.lectures.get(lecture_id)
        payload = {
            "lecture": None
            if lecture is None
            else {
                "id": lecture.id,
                "title": lecture.title,
                "date": lecture.date.isoformat(),
                "material_path": lecture.material_path,
            },
            "files": files,
        }
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def revision(self, lecture_id: str) -> str | None:
        local = self.local_revision(lecture_id)
        if local is None:
            return None
        alias = read_lecture_source_alias(
            self.layout.lecture_source_alias_path(self.course_id, lecture_id)
        )
        return alias.legacy if alias is not None and alias.local == local else local

    def _selected_files(self, lecture_id: str) -> list[dict]:
        if self.routing is None:
            manifest = read_lecture_source_manifest(
                self.layout.lecture_source_manifest_path(self.course_id, lecture_id),
                self.course_id,
                lecture_id,
            )
            indexed = self.indexed or {}
            return [
                {"path": item.path, "sha256": indexed.get(item.path, item.sha256), "route": None}
                for item in sorted(manifest.files, key=lambda item: item.path)
            ]
        return [
            {"path": route.path, "sha256": self._content(route), "route": _route(route)}
            for route in sorted(self.routing.routes, key=lambda item: item.path)
            if route.role == SourceRouteRole.COURSE_WIDE
            or (route.role == SourceRouteRole.LECTURE and route.lecture_id == lecture_id)
        ]

    def _content(self, route: CourseSourceRoute) -> str:
        if self.indexed is None:
            return route.sha256
        return self.indexed.get(route.path, "missing")


def lecture_source_revision(
    layout: StorageLayout, *, course_id: str, lecture_id: str
) -> str | None:
    return CourseSourceInputs.load(layout, course_id).revision(lecture_id)


def local_lecture_source_revision(
    layout: StorageLayout, *, course_id: str, lecture_id: str
) -> str | None:
    """The lecture-local revision without the legacy alias (used by the alias migration)."""
    return CourseSourceInputs.load(layout, course_id).local_revision(lecture_id)


def read_lecture_source_alias(path: Path) -> LectureSourceAlias | None:
    if not path.exists():
        return None
    try:
        return LectureSourceAlias.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None


def _route(route: CourseSourceRoute) -> dict:
    return {"kind": route.kind, "role": route.role.value, "lecture_id": route.lecture_id}


def _read_lectures(layout: StorageLayout, course_id: str) -> list[Lecture]:
    # Read-only: interrupted updates are recovered by every course-lock holder.
    path = layout.course_root(course_id) / "builder" / "course-workspace.json"
    if not path.exists():
        return []
    try:
        workspace = CourseWorkspaceResult.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return []
    return workspace.lectures if workspace.course.id == course_id else []


def _read_index(path: Path, course_id: str) -> dict[str, str] | None:
    if not path.exists():
        return None
    try:
        index = CourseSourceIndex.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None
    if index.course_id != course_id:
        return None
    return {item.path: item.sha256 for item in index.files}

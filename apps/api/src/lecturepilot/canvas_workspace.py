from __future__ import annotations

import json
import os
import re
from hashlib import sha256
from pathlib import Path

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.latex_canvas_importer import CANVAS_IMPORT_VERSION, import_latex_canvas
from lecturepilot.latex_canvas_text import (
    BROWSER_IMAGE_SUFFIXES,
    is_allowed_canvas_asset,
)


class CanvasWorkspaceError(RuntimeError):
    """Raised when course canvas material cannot be loaded safely."""


class CanvasWorkspace:
    def __init__(
        self,
        *,
        workspace_root: Path | None = None,
        material_root: Path | None = None,
    ) -> None:
        self.workspace_root = workspace_root or _default_workspace_root()
        self.material_root = material_root or _default_material_root()

    def read_document(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
    ) -> CanvasDocument:
        canvas_path = self._document_path(course_id, lecture_id, user_id)
        if canvas_path.exists():
            payload = json.loads(canvas_path.read_text())
            if payload.get("import_version") == CANVAS_IMPORT_VERSION:
                return CanvasDocument.model_validate(payload)

        source_path = self._source_path(lecture_id)
        document = import_latex_canvas(
            source_path=source_path,
            material_root=self.material_root,
            course_id=course_id,
            lecture_id=lecture_id,
            workspace_path=str(canvas_path),
        )
        canvas_path.parent.mkdir(parents=True, exist_ok=True)
        canvas_path.write_text(json.dumps(document.model_dump(), indent=2), encoding="utf-8")
        return document

    def apply_sections(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
        sections: list[CanvasSection],
    ) -> CanvasDocument:
        document = self.read_document(
            course_id=course_id,
            lecture_id=lecture_id,
            user_id=user_id,
        )
        existing = {section.id: section for section in document.sections}
        for section in sections:
            existing[section.id] = section
        document.sections = list(existing.values())
        path = Path(document.workspace_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document.model_dump(), indent=2), encoding="utf-8")
        return document

    def asset_path(self, *, lecture_id: str, asset_path: str) -> Path:
        if ".." in Path(asset_path).parts or asset_path.startswith("/"):
            raise CanvasWorkspaceError("Asset path must stay inside course material root.")
        if Path(asset_path).suffix.lower() not in BROWSER_IMAGE_SUFFIXES:
            raise CanvasWorkspaceError("Canvas assets are limited to browser image files.")
        source = self._source_path(lecture_id)
        candidate = source.parent / asset_path
        if is_allowed_canvas_asset(candidate):
            return candidate
        image_candidate = self.material_root / "images" / asset_path
        if is_allowed_canvas_asset(image_candidate):
            return image_candidate
        raise CanvasWorkspaceError("Canvas asset was not found.")

    def _document_path(self, course_id: str, lecture_id: str, user_id: str) -> Path:
        return (
            self.workspace_root
            / "students"
            / _pseudonymous_id(user_id)
            / "courses"
            / _safe_id(course_id)
            / "lectures"
            / _safe_id(lecture_id)
            / "canvas.json"
        )

    def _source_path(self, lecture_id: str) -> Path:
        source_name = _LECTURE_SOURCES.get(lecture_id)
        if source_name is None:
            raise CanvasWorkspaceError(f"No source mapping configured for {lecture_id}.")
        source_path = self.material_root / source_name
        if not source_path.exists():
            raise CanvasWorkspaceError(f"Course source not found: {source_path}")
        return source_path


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
    if not safe:
        raise CanvasWorkspaceError("Workspace id cannot be empty.")
    return safe[:120]


def _pseudonymous_id(user_id: str) -> str:
    return sha256(user_id.encode("utf-8")).hexdigest()[:24]


def _default_workspace_root() -> Path:
    configured = os.environ.get("LECTUREPILOT_WORKSPACE_ROOT")
    return Path(configured or ".lecturepilot/workspaces").expanduser()


def _default_material_root() -> Path:
    configured = os.environ.get("LECTUREPILOT_COURSE_MATERIAL_ROOT")
    if configured:
        return Path(configured).expanduser()
    candidates = Path.home().glob(
        "Documents/Studium/*/Kurse/Grundlagen des Maschinellen Lernens Vorlesung"
    )
    for candidate in candidates:
        if (candidate / "Lecture03-eng.tex").exists():
            return candidate
    return Path("local-course-materials/martius-ml").expanduser()


_LECTURE_SOURCES = {"lecture-03": "Lecture03-eng.tex"}

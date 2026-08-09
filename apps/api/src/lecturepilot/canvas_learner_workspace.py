from __future__ import annotations

import json
from pathlib import Path

from lecturepilot.canvas_learning_support import normalize_learning_support
from lecturepilot.canvas_markdown import (
    read_document_source,
    read_student_section_placements,
    write_document_source,
    write_student_sections,
)
from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.canvas_sections import merge_sections
from lecturepilot.canvas_signatures import official_canvas_signature, is_student_section
from lecturepilot.course_media import apply_course_media
from lecturepilot.latex_canvas_importer import CANVAS_IMPORT_VERSION
from lecturepilot.student_asset_refs import resolve_student_asset_refs


class CanvasLearnerWorkspaceMixin:
    def read_document(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
    ) -> CanvasDocument:
        canvas_dir = self._canvas_dir(course_id, lecture_id, user_id)
        manifest_path = canvas_dir / "index.md"
        if not manifest_path.exists() or self._is_stale_canvas_manifest(manifest_path):
            student_placements = read_student_section_placements(canvas_dir)
            student_sections = self.read_learner_overlay_sections(
                course_id=course_id,
                lecture_id=lecture_id,
                user_id=user_id,
            )
            document = self._initial_document(
                course_id=course_id,
                lecture_id=lecture_id,
                user_id=user_id,
            )
            if student_sections:
                document = document.model_copy(
                    update={"sections": merge_sections([*document.sections, *student_sections])}
                )
            self._write_initial_source(document, canvas_dir, student_placements=student_placements)

        document = apply_course_media(
            normalize_learning_support(read_document_source(canvas_dir)), self.material_root
        )
        document = apply_course_media(document, self.course_media_root(course_id))
        document = resolve_student_asset_refs(
            document,
            canvas_dir=canvas_dir,
            course_id=course_id,
            lecture_id=lecture_id,
            layout=self.layout,
            user_id=user_id,
        )
        self._write_compiled_document(document, course_id, lecture_id, user_id)
        return document

    def apply_sections(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
        sections: list[CanvasSection],
        placements: dict[str, object] | None = None,
    ) -> CanvasDocument:
        document = self.read_document(course_id=course_id, lecture_id=lecture_id, user_id=user_id)
        write_student_sections(
            Path(document.workspace_path).parent, sections, placements=placements
        )
        document = read_document_source(Path(document.workspace_path).parent)
        self._write_compiled_document(document, course_id, lecture_id, user_id)
        return document

    def read_learner_overlay_sections(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
    ) -> list[CanvasSection]:
        canvas_dir = self._canvas_dir(course_id, lecture_id, user_id)
        sections: list[CanvasSection] = []
        if (canvas_dir / "index.md").exists():
            sections.extend(
                section
                for section in read_document_source(canvas_dir).sections
                if is_student_section(section)
            )
        compiled_paths = [
            self._compiled_path(course_id, lecture_id, user_id),
            self.layout.legacy_compiled_canvas_path(user_id, course_id, lecture_id),
        ]
        for compiled_path in compiled_paths:
            if not compiled_path.exists():
                continue
            payload = json.loads(compiled_path.read_text(encoding="utf-8"))
            sections.extend(
                section
                for section in CanvasDocument.model_validate(payload).sections
                if is_student_section(section)
            )
        return merge_sections(sections)

    def _is_stale_canvas_manifest(self, manifest_path: Path) -> bool:
        document = read_document_source(manifest_path.parent)
        if document.import_version != CANVAS_IMPORT_VERSION:
            return True
        base = self.course_canvas_store.read(
            course_id=document.course_id,
            lecture_id=document.lecture_id,
            workspace_path=document.workspace_path,
        )
        if base is None:
            return False
        if document.source_kind != "generated":
            return True
        return official_canvas_signature(document) != official_canvas_signature(base)

    def _write_compiled_document(
        self,
        document: CanvasDocument,
        course_id: str,
        lecture_id: str,
        user_id: str,
    ) -> None:
        path = self._compiled_path(course_id, lecture_id, user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document.model_dump(), indent=2), encoding="utf-8")

    def _write_initial_source(
        self,
        document: CanvasDocument,
        canvas_dir: Path,
        *,
        student_placements: dict[str, object] | None = None,
    ) -> None:
        base_sections = [
            section for section in document.sections if not is_student_section(section)
        ]
        student_sections = [section for section in document.sections if is_student_section(section)]
        sections_dir = canvas_dir / "sections"
        if sections_dir.exists():
            for path in sections_dir.glob("*.md"):
                path.unlink(missing_ok=True)
        write_document_source(document.model_copy(update={"sections": base_sections}), canvas_dir)
        if student_sections:
            write_student_sections(canvas_dir, student_sections, placements=student_placements)

    def _lecture_workspace_dir(self, course_id: str, lecture_id: str, user_id: str) -> Path:
        return self.layout.user_lecture_root(user_id, course_id, lecture_id)

    def _canvas_dir(self, course_id: str, lecture_id: str, user_id: str) -> Path:
        return self._lecture_workspace_dir(course_id, lecture_id, user_id) / "canvas"

    def _compiled_path(self, course_id: str, lecture_id: str, user_id: str) -> Path:
        return self._lecture_workspace_dir(course_id, lecture_id, user_id) / "canvas.json"

from __future__ import annotations

from pathlib import Path

from lecturepilot.canvas_markdown import (
    place_student_sections,
    read_student_section_placements,
    read_student_sections,
    write_student_sections,
)
from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.canvas_snapshot import locked_canvas_access, locked_canvas_paths
from lecturepilot.course_canvas_context import InvalidPublishedCanvasContextError
from lecturepilot.course_media import apply_course_media
from lecturepilot.student_asset_refs import resolve_student_asset_refs


class CanvasLearnerWorkspaceMixin:
    def read_published_document(
        self,
        published: CanvasDocument,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
    ) -> CanvasDocument:
        canvas_dir = self._canvas_dir(course_id, lecture_id, user_id)
        with locked_canvas_access(canvas_dir):
            return self._merge_learner_markdown(
                published,
                canvas_dir=canvas_dir,
                course_id=course_id,
                lecture_id=lecture_id,
                user_id=user_id,
            )

    def read_document(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
    ) -> CanvasDocument:
        snapshot = self.course_canvas_store.read_current_published_snapshot(
            course_id=course_id,
            lecture_id=lecture_id,
        )
        if snapshot is None:
            raise InvalidPublishedCanvasContextError("Canvas has not been published.")
        return self.read_published_document(
            snapshot.document,
            course_id=course_id,
            lecture_id=lecture_id,
            user_id=user_id,
        )

    def apply_sections(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
        sections: list[CanvasSection],
        placements: dict[str, object] | None = None,
    ) -> CanvasDocument:
        snapshot = self.course_canvas_store.read_current_published_snapshot(
            course_id=course_id,
            lecture_id=lecture_id,
        )
        if snapshot is None:
            raise InvalidPublishedCanvasContextError("Canvas has not been published.")
        canvas_dir = self._canvas_dir(course_id, lecture_id, user_id)
        with locked_canvas_paths(canvas_dir):
            write_student_sections(canvas_dir, sections, placements=placements)
            return self._merge_learner_markdown(
                snapshot.document,
                canvas_dir=canvas_dir,
                course_id=course_id,
                lecture_id=lecture_id,
                user_id=user_id,
            )

    def read_learner_overlay_sections(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
    ) -> list[CanvasSection]:
        canvas_dir = self._canvas_dir(course_id, lecture_id, user_id)
        with locked_canvas_access(canvas_dir):
            return read_student_sections(
                canvas_dir,
                course_id=course_id,
                lecture_id=lecture_id,
            )

    def _merge_learner_markdown(
        self,
        published: CanvasDocument,
        *,
        canvas_dir: Path,
        course_id: str,
        lecture_id: str,
        user_id: str,
    ) -> CanvasDocument:
        document = published.model_copy(
            update={
                "sections": place_student_sections(
                    published.sections,
                    read_student_sections(
                        canvas_dir,
                        course_id=course_id,
                        lecture_id=lecture_id,
                    ),
                    read_student_section_placements(canvas_dir),
                )
            }
        )
        document = apply_course_media(document, self.material_root)
        document = apply_course_media(document, self.course_media_root(course_id))
        return resolve_student_asset_refs(
            document,
            canvas_dir=canvas_dir,
            course_id=course_id,
            lecture_id=lecture_id,
            layout=self.layout,
            user_id=user_id,
        )

    def _lecture_workspace_dir(self, course_id: str, lecture_id: str, user_id: str) -> Path:
        return self.layout.user_lecture_root(user_id, course_id, lecture_id)

    def _canvas_dir(self, course_id: str, lecture_id: str, user_id: str) -> Path:
        return self._lecture_workspace_dir(course_id, lecture_id, user_id) / "canvas"

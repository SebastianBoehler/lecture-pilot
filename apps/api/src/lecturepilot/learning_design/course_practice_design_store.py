from __future__ import annotations

from pathlib import Path

from lecturepilot.learning_design.course_learning_intent import has_approved_intent
from lecturepilot.learning_design.course_practice_design_files import locked_design_file
from lecturepilot.learning_design.course_practice_design_models import PracticeDesign
from lecturepilot.learning_design.course_practice_design_snapshot import (
    PracticeDesignApprovalRequired as PracticeDesignApprovalRequired,
    PracticeDesignStale as PracticeDesignStale,
    PracticeDesignSnapshot,
    PracticeDesignUnavailable as PracticeDesignUnavailable,
    read_practice_design,
    snapshot_practice_design,
)
from lecturepilot.core.storage_layout import StorageLayout


class PracticeDesignStore:
    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def read(self, *, course_id: str, lecture_id: str) -> PracticeDesign | None:
        path = self._path(course_id, lecture_id)
        with locked_design_file(path):
            return self._read(path, course_id, lecture_id)

    def snapshot(self, *, course_id: str, lecture_id: str) -> PracticeDesignSnapshot:
        path = self._path(course_id, lecture_id)
        with locked_design_file(path):
            return snapshot_practice_design(path, course_id=course_id, lecture_id=lecture_id)

    def require_approved(
        self,
        *,
        course_id: str,
        lecture_id: str,
        source_revision: str,
        design_revision: str | None = None,
        allow_pending_implementation: bool = False,
    ) -> PracticeDesign:
        path = self._path(course_id, lecture_id)
        with locked_design_file(path):
            current = self._required(path, course_id, lecture_id)
            if current.source_revision != source_revision or (
                design_revision is not None and current.revision != design_revision
            ):
                raise PracticeDesignStale(
                    "The practice design or source revision changed. Reload it."
                )
            if not has_approved_intent(current):
                raise PracticeDesignApprovalRequired(
                    "Approve the current learning goals before generating the canvas."
                )
            review = current.quality_review
            if not allow_pending_implementation and (
                review is None or review.practice_design_revision != current.revision
            ):
                raise PracticeDesignApprovalRequired(
                    "Teaching implementation needs automatic repair."
                )
            return current

    def _path(self, course_id: str, lecture_id: str) -> Path:
        return self.layout.lecture_practice_design_path(course_id, lecture_id)

    def _required(self, path: Path, course_id: str, lecture_id: str) -> PracticeDesign:
        design = self._read(path, course_id, lecture_id)
        if design is None:
            raise PracticeDesignApprovalRequired(
                "Generate and approve the lecture learning plan before generating its canvas."
            )
        return design

    @staticmethod
    def _read(path: Path, course_id: str, lecture_id: str) -> PracticeDesign | None:
        return read_practice_design(path, course_id=course_id, lecture_id=lecture_id)

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_practice_design_files import locked_design_file, write_design_file
from lecturepilot.course_practice_design_models import (
    PracticeDesign,
    PracticeDesignApproval,
    PracticeDesignProposal,
    PracticeDesignUpdate,
    PracticeTarget,
)
from lecturepilot.course_practice_design_review_binding import with_quality_review
from lecturepilot.course_practice_design_review_models import (
    PracticeDesignQualityReview,
    PracticeDesignReviewResult,
)
from lecturepilot.course_practice_design_snapshot import (
    PracticeDesignError,
    PracticeDesignSnapshot,
    PracticeDesignUnavailable as PracticeDesignUnavailable,
    read_practice_design,
    snapshot_practice_design,
)
from lecturepilot.course_practice_design_validation import (
    PracticeDesignValidationError,
    validate_practice_design,
    validate_practice_design_review,
)
from lecturepilot.storage_layout import StorageLayout


class PracticeDesignStale(PracticeDesignError):
    pass


class PracticeDesignApprovalRequired(PracticeDesignError):
    pass


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

    def save_proposal(
        self,
        *,
        course_id: str,
        lecture_id: str,
        source_revision: str,
        proposal: PracticeDesignProposal,
        review: PracticeDesignReviewResult,
        source: CanvasDocument,
        allowed_source_paths: Iterable[str],
        expected_design_revision: str | None,
        expected_design_approval: PracticeDesignApproval | None,
        expected_design_review: PracticeDesignQualityReview | None,
        expected_invalid_digest: str | None = None,
    ) -> PracticeDesign:
        design = PracticeDesign.create(
            course_id=course_id,
            lecture_id=lecture_id,
            source_revision=source_revision,
            **proposal.model_dump(mode="python"),
        )
        validate_practice_design(design, source=source, allowed_source_paths=allowed_source_paths)
        validate_practice_design_review(
            review,
            design,
            source=source,
            allowed_source_paths=allowed_source_paths,
        )
        design = with_quality_review(design, review)
        path = self._path(course_id, lecture_id)
        with locked_design_file(path):
            if expected_invalid_digest is not None:
                current_snapshot = snapshot_practice_design(
                    path, course_id=course_id, lecture_id=lecture_id
                )
                if current_snapshot.invalid_digest != expected_invalid_digest:
                    raise PracticeDesignStale(
                        "The practice design changed while the learning plan was proposed. Reload it."
                    )
            else:
                current = self._read(path, course_id, lecture_id)
                if expected_design_revision is None:
                    if (
                        current is not None
                        or expected_design_approval is not None
                        or expected_design_review is not None
                    ):
                        raise PracticeDesignStale(
                            "The practice design changed while the learning plan was proposed. Reload it."
                        )
                elif (
                    current is None
                    or current.revision != expected_design_revision
                    or current.approval != expected_design_approval
                    or current.quality_review != expected_design_review
                ):
                    raise PracticeDesignStale(
                        "The practice design changed while the learning plan was proposed. Reload it."
                    )
            write_design_file(path, design)
        return design

    def update(
        self,
        *,
        course_id: str,
        lecture_id: str,
        current_source_revision: str,
        update: PracticeDesignUpdate,
        source: CanvasDocument,
        allowed_source_paths: Iterable[str],
    ) -> PracticeDesign:
        path = self._path(course_id, lecture_id)
        with locked_design_file(path):
            current = self._required(path, course_id, lecture_id)
            if (
                current.source_revision != current_source_revision
                or update.source_revision != current_source_revision
                or update.practice_design_revision != current.revision
            ):
                raise PracticeDesignStale(
                    "The practice design or source revision changed. Reload it."
                )
            if _identity_skeleton(current.targets) != _identity_skeleton(update.targets):
                raise PracticeDesignValidationError(
                    "Stable practice design IDs cannot be added, removed, renamed, or reordered."
                )
            changed = PracticeDesign.create(
                course_id=course_id,
                lecture_id=lecture_id,
                source_revision=current_source_revision,
                lecture_title=update.lecture_title,
                objective=update.objective,
                planning_context=update.planning_context,
                targets=update.targets,
            )
            validate_practice_design(
                changed, source=source, allowed_source_paths=allowed_source_paths
            )
            write_design_file(path, changed)
            return changed

    def save_review(
        self,
        *,
        course_id: str,
        lecture_id: str,
        source_revision: str,
        design_revision: str,
        review: PracticeDesignReviewResult,
        source: CanvasDocument,
        allowed_source_paths: Iterable[str],
        expected_design_review: PracticeDesignQualityReview | None,
        expected_design_approval: PracticeDesignApproval | None,
    ) -> PracticeDesign:
        path = self._path(course_id, lecture_id)
        with locked_design_file(path):
            current = self._required(path, course_id, lecture_id)
            if (
                current.source_revision != source_revision
                or current.revision != design_revision
                or current.quality_review != expected_design_review
                or current.approval != expected_design_approval
            ):
                raise PracticeDesignStale(
                    "The practice design or source revision changed. Reload it."
                )
            validate_practice_design_review(
                review,
                current,
                source=source,
                allowed_source_paths=allowed_source_paths,
            )
            reviewed = with_quality_review(current.model_copy(update={"approval": None}), review)
            write_design_file(path, reviewed)
            return reviewed

    def approve(
        self,
        *,
        course_id: str,
        lecture_id: str,
        source_revision: str,
        design_revision: str,
        approved_by: str,
    ) -> PracticeDesign:
        path = self._path(course_id, lecture_id)
        with locked_design_file(path):
            current = self._required(path, course_id, lecture_id)
            if current.source_revision != source_revision or current.revision != design_revision:
                raise PracticeDesignStale(
                    "The practice design or source revision changed. Reload it."
                )
            review = current.quality_review
            if (
                review is None
                or review.source_revision != current.source_revision
                or review.practice_design_revision != current.revision
            ):
                raise PracticeDesignApprovalRequired(
                    "Review the current practice design before approval."
                )
            if review.has_critical_issues:
                raise PracticeDesignApprovalRequired(
                    "Resolve critical semantic review issues before approval."
                )
            approved = current.model_copy(
                update={
                    "approval": PracticeDesignApproval(
                        approved_by=approved_by,
                        approved_at=datetime.now(UTC),
                        source_revision=current.source_revision,
                        practice_design_revision=current.revision,
                    )
                }
            )
            write_design_file(path, approved)
            return approved

    def require_approved(
        self,
        *,
        course_id: str,
        lecture_id: str,
        source_revision: str,
        design_revision: str | None = None,
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
            approval = current.approval
            if approval is None or (
                approval.source_revision != current.source_revision
                or approval.practice_design_revision != current.revision
            ):
                raise PracticeDesignApprovalRequired(
                    "Approve the current practice design before generating the canvas."
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


def _identity_skeleton(targets: Sequence[PracticeTarget]) -> tuple:
    return tuple(
        (
            target.id,
            tuple(item.id for item in target.evidence_criteria),
            tuple(item.id for item in target.misconceptions),
        )
        for target in targets
    )

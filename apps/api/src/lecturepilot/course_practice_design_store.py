from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
import fcntl
import os
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from lecturepilot.course_practice_design_models import (
    PracticeDesign,
    PracticeDesignApproval,
    PracticeDesignProposal,
    PracticeDesignUpdate,
    PracticeTarget,
)
from lecturepilot.course_practice_design_validation import (
    PracticeDesignValidationError,
    validate_practice_design,
)
from lecturepilot.durable_files import ensure_durable_directory, fsync_directory
from lecturepilot.storage_layout import StorageLayout


class PracticeDesignError(ValueError):
    pass


class PracticeDesignUnavailable(PracticeDesignError):
    pass


class PracticeDesignStale(PracticeDesignError):
    pass


class PracticeDesignApprovalRequired(PracticeDesignError):
    pass


class PracticeDesignStore:
    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def read(self, *, course_id: str, lecture_id: str) -> PracticeDesign | None:
        path = self._path(course_id, lecture_id)
        with self._locked(path):
            return self._read(path, course_id, lecture_id)

    def save_proposal(
        self,
        *,
        course_id: str,
        lecture_id: str,
        source_revision: str,
        proposal: PracticeDesignProposal,
        allowed_source_paths: Iterable[str],
        expected_design_revision: str | None,
        expected_design_approval: PracticeDesignApproval | None,
    ) -> PracticeDesign:
        design = PracticeDesign.create(
            course_id=course_id,
            lecture_id=lecture_id,
            source_revision=source_revision,
            **proposal.model_dump(mode="python"),
        )
        validate_practice_design(design, allowed_source_paths)
        path = self._path(course_id, lecture_id)
        with self._locked(path):
            current = self._read(path, course_id, lecture_id)
            if expected_design_revision is None:
                if current is not None or expected_design_approval is not None:
                    raise PracticeDesignStale(
                        "The practice design changed while the learning plan was proposed. Reload it."
                    )
            elif (
                current is None
                or current.revision != expected_design_revision
                or current.approval != expected_design_approval
            ):
                raise PracticeDesignStale(
                    "The practice design changed while the learning plan was proposed. Reload it."
                )
            self._write(path, design)
        return design

    def update(
        self,
        *,
        course_id: str,
        lecture_id: str,
        current_source_revision: str,
        update: PracticeDesignUpdate,
        allowed_source_paths: Iterable[str],
    ) -> PracticeDesign:
        path = self._path(course_id, lecture_id)
        with self._locked(path):
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
                targets=update.targets,
            )
            validate_practice_design(changed, allowed_source_paths)
            self._write(path, changed)
            return changed

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
        with self._locked(path):
            current = self._required(path, course_id, lecture_id)
            if current.source_revision != source_revision or current.revision != design_revision:
                raise PracticeDesignStale(
                    "The practice design or source revision changed. Reload it."
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
            self._write(path, approved)
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
        with self._locked(path):
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

    @contextmanager
    def _locked(self, path: Path) -> Iterator[None]:
        ensure_durable_directory(path.parent)
        descriptor = os.open(path.parent / ".practice-design.lock", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def _required(self, path: Path, course_id: str, lecture_id: str) -> PracticeDesign:
        design = self._read(path, course_id, lecture_id)
        if design is None:
            raise PracticeDesignApprovalRequired(
                "Generate and approve the lecture learning plan before generating its canvas."
            )
        return design

    @staticmethod
    def _read(path: Path, course_id: str, lecture_id: str) -> PracticeDesign | None:
        if not path.exists():
            return None
        try:
            design = PracticeDesign.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            raise PracticeDesignUnavailable(
                "Stored practice design is invalid. Generate a new learning plan."
            ) from exc
        if design.course_id != course_id or design.lecture_id != lecture_id:
            raise PracticeDesignUnavailable("Stored practice design identity is invalid.")
        return design

    @staticmethod
    def _write(path: Path, design: PracticeDesign) -> None:
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(design.model_dump_json(indent=2))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            fsync_directory(path.parent)
        finally:
            temporary.unlink(missing_ok=True)


def _identity_skeleton(targets: Sequence[PracticeTarget]) -> tuple:
    return tuple(
        (
            target.id,
            tuple(item.id for item in target.evidence_criteria),
            tuple(item.id for item in target.misconceptions),
        )
        for target in targets
    )

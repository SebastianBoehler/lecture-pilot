from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from pydantic import ValidationError

from lecturepilot.course_practice_design_models import PracticeDesign


class PracticeDesignError(ValueError):
    pass


class PracticeDesignStale(PracticeDesignError):
    pass


class PracticeDesignApprovalRequired(PracticeDesignError):
    pass


class PracticeDesignUnavailable(PracticeDesignError):
    pass


@dataclass(frozen=True)
class PracticeDesignSnapshot:
    design: PracticeDesign | None
    invalid_digest: str | None


def read_practice_design(path: Path, *, course_id: str, lecture_id: str) -> PracticeDesign | None:
    payload = _read_payload(path)
    if payload is None:
        return None
    return _parse_design(payload, course_id=course_id, lecture_id=lecture_id)


def snapshot_practice_design(
    path: Path, *, course_id: str, lecture_id: str
) -> PracticeDesignSnapshot:
    payload = _read_payload(path)
    if payload is None:
        return PracticeDesignSnapshot(design=None, invalid_digest=None)
    try:
        design = _parse_design(payload, course_id=course_id, lecture_id=lecture_id)
    except PracticeDesignUnavailable:
        return PracticeDesignSnapshot(design=None, invalid_digest=sha256(payload).hexdigest())
    return PracticeDesignSnapshot(design=design, invalid_digest=None)


def _read_payload(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise PracticeDesignUnavailable(
            "Stored practice design could not be read. Generate a new learning plan."
        ) from exc


def _parse_design(payload: bytes, *, course_id: str, lecture_id: str) -> PracticeDesign:
    try:
        design = PracticeDesign.model_validate_json(payload)
    except ValidationError as exc:
        raise PracticeDesignUnavailable(
            "Stored practice design is invalid. Generate a new learning plan."
        ) from exc
    if design.course_id != course_id or design.lecture_id != lecture_id:
        raise PracticeDesignUnavailable("Stored practice design identity is invalid.")
    review = design.quality_review
    if review is not None:
        if (
            review.source_revision != design.source_revision
            or review.practice_design_revision != design.revision
        ):
            raise PracticeDesignUnavailable("Stored practice design review is stale.")
        if design.approval is not None and review.has_critical_issues:
            raise PracticeDesignUnavailable("Stored practice design review blocks approval.")
    elif design.approval is not None:
        raise PracticeDesignUnavailable("Stored approved practice design has no quality review.")
    return design


def require_proposal_snapshot(
    path,
    *,
    course_id,
    lecture_id,
    expected_design_revision,
    expected_design_approval,
    expected_design_review,
    expected_learning_intent,
    expected_invalid_digest,
):
    snapshot = snapshot_practice_design(path, course_id=course_id, lecture_id=lecture_id)
    message = "The practice design changed while the learning plan was proposed. Reload it."
    if expected_invalid_digest is not None:
        if snapshot.invalid_digest != expected_invalid_digest:
            raise PracticeDesignStale(message)
        return
    if snapshot.invalid_digest is not None:
        raise PracticeDesignUnavailable(
            "Stored practice design is invalid. Generate a new learning plan."
        )
    current = snapshot.design
    if expected_design_revision is None:
        if any(
            item is not None
            for item in (
                current,
                expected_design_approval,
                expected_design_review,
                expected_learning_intent,
            )
        ):
            raise PracticeDesignStale(message)
    elif (
        current is None
        or current.revision != expected_design_revision
        or current.approval != expected_design_approval
        or current.quality_review != expected_design_review
        or current.learning_intent != expected_learning_intent
    ):
        raise PracticeDesignStale(message)

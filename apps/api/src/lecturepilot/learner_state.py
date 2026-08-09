from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from pydantic import ValidationError

from lecturepilot.durable_files import atomic_write_json, exclusive_file_lock
from lecturepilot.learner_lesson_state_models import (
    LearnerQuizState,
    LearnerQuizStorePayload,
    QuizCorrectionState,
)
from lecturepilot.learner_gate_state_models import LearnerGateStorePayload
from lecturepilot.models import AttendanceStatus, QualityGateDecision
from lecturepilot.storage_layout import StorageLayout


class LearnerStateStore:
    """Persists per-user, per-lecture attendance and quality gate state."""

    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def write_attendance(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
        attendance: AttendanceStatus,
    ) -> None:
        path = self.layout.user_lecture_root(user_id, course_id, lecture_id) / "attendance.json"
        with exclusive_file_lock(path):
            _write_json(
                path,
                {
                    "course_id": course_id,
                    "lecture_id": lecture_id,
                    "attendance": attendance.value,
                    "updated_at": _now(),
                },
            )

    def record_quality_gate(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
        decision: QualityGateDecision,
    ) -> None:
        path = self.layout.user_lecture_root(user_id, course_id, lecture_id) / "gates.json"
        with exclusive_file_lock(path):
            payload = _read_gate_payload(path, course_id=course_id, lecture_id=lecture_id)
            gates = dict(payload.gates)
            gates[decision.gate_id] = decision
            stored = LearnerGateStorePayload(
                schema_version=1,
                course_id=course_id,
                lecture_id=lecture_id,
                updated_at=datetime.now(UTC),
                gates=gates,
            )
            _write_json(path, stored.model_dump(mode="json"))

    def latest_gate_decisions(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
    ) -> dict[str, QualityGateDecision]:
        path = self.layout.user_lecture_root(user_id, course_id, lecture_id) / "gates.json"
        return dict(_read_gate_payload(path, course_id=course_id, lecture_id=lecture_id).gates)

    def record_quiz_answer(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
        quiz_id: str,
        publication_version: int,
        attempt_id: str,
        selected_index: int,
        correct: bool | None,
    ) -> tuple[LearnerQuizState, bool]:
        path = self.layout.user_lecture_root(user_id, course_id, lecture_id) / "quizzes.json"
        with exclusive_file_lock(path):
            payload = _read_quiz_payload(path, course_id=course_id, lecture_id=lecture_id)
            quizzes = dict(payload.quizzes)
            attempts = {
                stored_quiz_id: dict(stored_attempts)
                for stored_quiz_id, stored_attempts in payload.attempts.items()
            }
            block_attempts = dict(attempts.get(quiz_id, {}))
            bound_quiz_id, bound_state = _bound_attempt(attempts, attempt_id)
            if bound_state is not None and bound_quiz_id != quiz_id:
                raise ValueError("Quiz attempt ID is already bound to another quiz.")
            if attempt_id in block_attempts:
                prior = block_attempts[attempt_id]
                if prior.publication_version != publication_version:
                    raise ValueError("Quiz attempt ID is already bound to another publication.")
                if prior.selected_index != selected_index:
                    raise ValueError("Quiz attempt ID was already used for a different answer.")
                return prior, False
            previous = _current_quiz_state(quizzes.get(quiz_id), publication_version)
            if previous is not None and previous.correct is True:
                return previous, False
            attempt_index = (previous.attempt_index if previous else 0) + 1
            first_correct = correct if previous is None else previous.first_attempt_correct
            state = LearnerQuizState(
                selected_index=selected_index,
                correct=correct,
                publication_version=publication_version,
                attempt_index=attempt_index,
                first_attempt_correct=first_correct,
                latest_outcome=(
                    "correct"
                    if correct is True
                    else "incorrect"
                    if correct is False
                    else "unscored"
                ),
                correction_state=_correction_state(previous, correct),
            )
            quizzes[quiz_id] = state
            block_attempts[attempt_id] = state
            attempts[quiz_id] = block_attempts
            stored = LearnerQuizStorePayload(
                course_id=course_id,
                lecture_id=lecture_id,
                updated_at=datetime.now(UTC),
                quizzes=quizzes,
                attempts=attempts,
            )
            _write_json(path, stored.model_dump(mode="json"))
            return state, True

    def latest_quiz_states(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
        publication_version: int,
    ) -> dict[str, LearnerQuizState]:
        path = self.layout.user_lecture_root(user_id, course_id, lecture_id) / "quizzes.json"
        payload = _read_quiz_payload(path, course_id=course_id, lecture_id=lecture_id)
        quizzes = {
            block_id: state
            for block_id, state in payload.quizzes.items()
            if state.publication_version == publication_version
        }
        return dict(sorted(quizzes.items()))


class InvalidLearnerQuizStateError(ValueError):
    pass


class InvalidLearnerGateStateError(ValueError):
    pass


def _read_gate_payload(path: Path, *, course_id: str, lecture_id: str) -> LearnerGateStorePayload:
    if not path.exists():
        return LearnerGateStorePayload.empty(
            course_id=course_id,
            lecture_id=lecture_id,
            updated_at=datetime.now(UTC),
        )
    try:
        payload = LearnerGateStorePayload.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValidationError) as exc:
        raise InvalidLearnerGateStateError("Persisted learner gate state is invalid.") from exc
    if payload.course_id != course_id or payload.lecture_id != lecture_id:
        raise InvalidLearnerGateStateError("Persisted learner gate state is invalid.")
    return payload


def _read_quiz_payload(path: Path, *, course_id: str, lecture_id: str) -> LearnerQuizStorePayload:
    if not path.exists():
        return LearnerQuizStorePayload(
            course_id=course_id,
            lecture_id=lecture_id,
            updated_at=datetime.now(UTC),
            quizzes={},
            attempts={},
        )
    try:
        payload = LearnerQuizStorePayload.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValidationError) as exc:
        raise InvalidLearnerQuizStateError("Persisted learner quiz state is invalid.") from exc
    if payload.course_id != course_id or payload.lecture_id != lecture_id:
        raise InvalidLearnerQuizStateError("Persisted learner quiz state is invalid.")
    return payload


def _current_quiz_state(
    state: LearnerQuizState | None, publication_version: int
) -> LearnerQuizState | None:
    return state if state is not None and state.publication_version == publication_version else None


def _bound_attempt(
    attempts: dict[str, dict[str, LearnerQuizState]], attempt_id: str
) -> tuple[str | None, LearnerQuizState | None]:
    for quiz_id, quiz_attempts in attempts.items():
        state = quiz_attempts.get(attempt_id)
        if state is not None:
            return quiz_id, state
    return None, None


def _correction_state(
    previous: LearnerQuizState | None, correct: bool | None
) -> QuizCorrectionState:
    if correct is None:
        return "not_needed"
    if correct is False:
        return "needed"
    if previous is not None and previous.first_attempt_correct is False:
        return "corrected"
    return "not_needed"


def _write_json(path: Path, payload: dict) -> None:
    atomic_write_json(path, payload)


def _now() -> str:
    return datetime.now(UTC).isoformat()

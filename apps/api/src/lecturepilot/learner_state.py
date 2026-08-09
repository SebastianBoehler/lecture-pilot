from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import json

from pydantic import ValidationError

from lecturepilot.durable_files import atomic_write_json, exclusive_file_lock
from lecturepilot.learner_lesson_state_models import LearnerQuizState, QuizCorrectionState
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
            payload = _read_json(path)
            gates = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
            gates[decision.gate_id] = decision.model_dump(mode="json")
            _write_json(
                path,
                {
                    "course_id": course_id,
                    "lecture_id": lecture_id,
                    "updated_at": _now(),
                    "gates": gates,
                },
            )

    def latest_gate_decisions(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
    ) -> dict[str, QualityGateDecision]:
        path = self.layout.user_lecture_root(user_id, course_id, lecture_id) / "gates.json"
        payload = _read_json(path)
        raw_gates = payload.get("gates")
        if not isinstance(raw_gates, dict):
            return {}
        decisions: dict[str, QualityGateDecision] = {}
        for gate_id, raw_decision in raw_gates.items():
            if not isinstance(gate_id, str) or not isinstance(raw_decision, dict):
                continue
            try:
                decision = QualityGateDecision.model_validate(raw_decision)
            except ValidationError:
                continue
            if decision.gate_id == gate_id:
                decisions[gate_id] = decision
        return decisions

    def record_quiz_answer(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
        block_id: str,
        attempt_id: str,
        selected_index: int,
        correct: bool | None,
    ) -> tuple[LearnerQuizState, bool]:
        path = self.layout.user_lecture_root(user_id, course_id, lecture_id) / "quizzes.json"
        with exclusive_file_lock(path):
            payload = _read_json(path)
            quizzes = payload.get("quizzes") if isinstance(payload.get("quizzes"), dict) else {}
            attempts = payload.get("attempts") if isinstance(payload.get("attempts"), dict) else {}
            block_attempts = (
                attempts.get(block_id) if isinstance(attempts.get(block_id), dict) else {}
            )
            if attempt_id in block_attempts:
                prior = LearnerQuizState.model_validate(block_attempts[attempt_id])
                if prior.selected_index != selected_index:
                    raise ValueError("Quiz attempt ID was already used for a different answer.")
                return prior, False
            previous = _validated_quiz_state(quizzes.get(block_id))
            attempt_index = (previous.attempt_index if previous else 0) + 1
            first_correct = correct if previous is None else previous.first_attempt_correct
            state = LearnerQuizState(
                selected_index=selected_index,
                correct=correct,
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
            quizzes[block_id] = state.model_dump(mode="json")
            block_attempts[attempt_id] = state.model_dump(mode="json")
            attempts[block_id] = block_attempts
            _write_json(
                path,
                {
                    "course_id": course_id,
                    "lecture_id": lecture_id,
                    "updated_at": _now(),
                    "quizzes": quizzes,
                    "attempts": attempts,
                },
            )
            return state, True

    def latest_quiz_states(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
    ) -> dict[str, LearnerQuizState]:
        path = self.layout.user_lecture_root(user_id, course_id, lecture_id) / "quizzes.json"
        raw_quizzes = _read_json(path).get("quizzes")
        if not isinstance(raw_quizzes, dict):
            return {}
        quizzes = {}
        for block_id, raw_state in raw_quizzes.items():
            if not isinstance(block_id, str) or not isinstance(raw_state, dict):
                continue
            try:
                quizzes[block_id] = LearnerQuizState.model_validate(raw_state)
            except ValidationError:
                continue
        return dict(sorted(quizzes.items()))


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _validated_quiz_state(value) -> LearnerQuizState | None:
    if not isinstance(value, dict):
        return None
    try:
        return LearnerQuizState.model_validate(value)
    except ValidationError:
        return None


def _correction_state(
    previous: LearnerQuizState | None, correct: bool | None
) -> QuizCorrectionState:
    if correct is not True:
        return "needed"
    if previous is not None and previous.first_attempt_correct is False:
        return "corrected"
    return "not_needed"


def _write_json(path: Path, payload: dict) -> None:
    atomic_write_json(path, payload)


def _now() -> str:
    return datetime.now(UTC).isoformat()

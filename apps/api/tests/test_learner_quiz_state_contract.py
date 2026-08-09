import pytest
from pydantic import ValidationError

from lecturepilot.learner_lesson_state_models import LearnerQuizState


VALID_STATE = {
    "selected_index": 1,
    "correct": True,
    "publication_version": 3,
    "attempt_index": 1,
    "first_attempt_correct": True,
    "latest_outcome": "correct",
    "correction_state": "not_needed",
}


@pytest.mark.parametrize(
    "mutation",
    [
        {"publication_version": None},
        {"attempt_index": None},
        {"first_attempt_correct": None},
        {"latest_outcome": None},
        {"correction_state": None},
        {"publication_version": "3"},
        {"attempt_index": 1.0},
        {"selected_index": True},
        {"unexpected": "removed-field"},
    ],
)
def test_persisted_quiz_state_requires_the_exact_current_schema(mutation: dict) -> None:
    payload = {**VALID_STATE, **mutation}
    if mutation.get("first_attempt_correct", "present") is None:
        payload.pop("first_attempt_correct")
    if mutation.get("latest_outcome", "present") is None:
        payload.pop("latest_outcome")
    if mutation.get("correction_state", "present") is None:
        payload.pop("correction_state")
    if mutation.get("publication_version", "present") is None:
        payload.pop("publication_version")
    if mutation.get("attempt_index", "present") is None:
        payload.pop("attempt_index")

    with pytest.raises(ValidationError):
        LearnerQuizState.model_validate(payload)

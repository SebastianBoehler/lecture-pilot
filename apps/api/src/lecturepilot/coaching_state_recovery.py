from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from lecturepilot.coaching_progress import CoachingProgressStore, InvalidCoachingStateError
from lecturepilot.coaching_state_models import CoachingProgress
from lecturepilot.durable_files import atomic_write_json, exclusive_file_lock
from lecturepilot.learner_state import LearnerStateStore
from lecturepilot.learning_map import LearningMap
from lecturepilot.learning_state_preflight import validate_coaching_bindings
from lecturepilot.storage_layout import StorageLayout


class CoachingStateRecoveryNotRequired(ValueError):
    pass


class CoachingStateRecoveryResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    course_id: str
    lecture_id: str
    coaching_state_reset: bool
    cleared_gate_ids: list[str]


def recovery_required_detail(course_id: str, lecture_id: str) -> dict[str, str]:
    return {
        "code": "coaching_state_recovery_required",
        "message": (
            "Persisted coaching state cannot be resumed safely. Use the authenticated "
            "recovery endpoint before continuing."
        ),
        "recovery_path": (f"/courses/{course_id}/lectures/{lecture_id}/learner-state/recover"),
    }


def recover_invalid_coaching_state(
    *,
    layout: StorageLayout,
    learner_store: LearnerStateStore,
    learning_map: LearningMap,
    user_id: str,
    course_id: str,
    lecture_id: str,
) -> CoachingStateRecoveryResult:
    coaching_store = CoachingProgressStore(layout)
    try:
        progress = coaching_store.read(
            user_id=user_id,
            course_id=course_id,
            lecture_id=lecture_id,
        )
        validate_coaching_bindings(progress, learning_map)
    except InvalidCoachingStateError:
        pass
    else:
        raise CoachingStateRecoveryNotRequired
    current_revisions = {gate.id: gate.revision for gate in learning_map.gates}
    cleared = learner_store.clear_quality_gates_matching_revisions(
        user_id=user_id,
        course_id=course_id,
        lecture_id=lecture_id,
        gate_revisions=current_revisions,
    )
    _write_empty_coaching_state(
        layout=layout,
        user_id=user_id,
        course_id=course_id,
        lecture_id=lecture_id,
    )
    return CoachingStateRecoveryResult(
        course_id=course_id,
        lecture_id=lecture_id,
        coaching_state_reset=True,
        cleared_gate_ids=cleared,
    )


def _write_empty_coaching_state(
    *, layout: StorageLayout, user_id: str, course_id: str, lecture_id: str
) -> None:
    path = layout.user_lecture_root(user_id, course_id, lecture_id) / "tutor-state.json"
    empty = CoachingProgress.empty(course_id=course_id, lecture_id=lecture_id)
    with exclusive_file_lock(path):
        atomic_write_json(path, empty.model_dump(mode="json"))

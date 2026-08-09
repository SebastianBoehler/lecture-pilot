import json

import pytest
from pydantic import ValidationError

from lecturepilot.learner_state import LearnerStateStore
from lecturepilot.models import QualityGateDecision
from lecturepilot.storage_layout import StorageLayout


def test_quality_gate_decision_requires_revision_and_forbids_prompt_compatibility() -> None:
    payload = {
        "gate_id": "gate-1",
        "gate_revision": "a" * 64,
        "status": "passed",
        "reason": "All required evidence is present.",
        "evidence_ids": ["mechanism"],
        "missing_evidence_ids": [],
    }
    with pytest.raises(ValidationError):
        QualityGateDecision.model_validate(
            {key: value for key, value in payload.items() if key != "gate_revision"}
        )
    with pytest.raises(ValidationError):
        QualityGateDecision.model_validate({**payload, "next_prompt": "legacy coupled prompt"})


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        json.dumps({"gates": {}}).encode(),
        json.dumps(
            {
                "schema_version": 1,
                "course_id": "course-1",
                "lecture_id": "lecture-1",
                "updated_at": "2026-08-09T08:00:00+00:00",
                "gates": {
                    "gate-1": {
                        "gate_id": "gate-1",
                        "status": "passed",
                        "reason": "revision omitted",
                        "evidence_ids": [],
                        "missing_evidence_ids": [],
                    }
                },
            }
        ).encode(),
    ],
)
def test_gate_store_rejects_corrupt_or_obsolete_state_without_rewriting(
    tmp_path, payload: bytes
) -> None:
    store = LearnerStateStore(StorageLayout(tmp_path))
    path = store.layout.user_lecture_root("student-1", "course-1", "lecture-1") / "gates.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(payload)

    with pytest.raises(ValueError, match="gate state"):
        store.latest_gate_decisions(
            user_id="student-1", course_id="course-1", lecture_id="lecture-1"
        )

    assert path.read_bytes() == payload

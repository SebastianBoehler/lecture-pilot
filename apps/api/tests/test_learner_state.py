from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from lecturepilot.learner_state import InvalidLearnerGateStateError, LearnerStateStore
from lecturepilot.models import QualityGateDecision, QualityGateStatus
from lecturepilot.storage_layout import StorageLayout


def test_concurrent_quality_gate_updates_preserve_every_gate(tmp_path: Path) -> None:
    store = LearnerStateStore(StorageLayout(tmp_path))

    def record(index: int) -> None:
        store.record_quality_gate(
            course_id="course-1",
            lecture_id="lecture-1",
            user_id="student-1",
            decision=_decision(f"gate-{index}", format(index, "x") * 64),
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(record, range(8)))

    decisions = store.latest_gate_decisions(
        course_id="course-1", lecture_id="lecture-1", user_id="student-1"
    )
    assert set(decisions) == {f"gate-{index}" for index in range(8)}


def test_invalid_gate_payload_fails_instead_of_skipping_records(tmp_path: Path) -> None:
    store = LearnerStateStore(StorageLayout(tmp_path))
    path = store.layout.user_lecture_root("student-1", "course-1", "lecture-1") / "gates.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"gates": {"broken": {"status": "passed"}}}', encoding="utf-8")

    with pytest.raises(InvalidLearnerGateStateError):
        store.latest_gate_decisions(
            course_id="course-1", lecture_id="lecture-1", user_id="student-1"
        )


def test_quality_gate_revision_survives_persistence(tmp_path: Path) -> None:
    store = LearnerStateStore(StorageLayout(tmp_path))
    store.record_quality_gate(
        course_id="course-1",
        lecture_id="lecture-1",
        user_id="student-1",
        decision=_decision("gate-1", "a" * 64),
    )

    decisions = store.latest_gate_decisions(
        course_id="course-1", lecture_id="lecture-1", user_id="student-1"
    )
    assert decisions["gate-1"].gate_revision == "a" * 64


def _decision(gate_id: str, revision: str) -> QualityGateDecision:
    return QualityGateDecision(
        gate_id=gate_id,
        gate_revision=revision,
        status=QualityGateStatus.PASSED,
        reason="Complete evidence.",
        evidence_ids=[f"{gate_id}-evidence"],
        missing_evidence_ids=[],
    )

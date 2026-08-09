from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time

import pytest

import lecturepilot.learner_state as learner_state
from lecturepilot.learner_state import LearnerStateStore
from lecturepilot.models import QualityGateDecision, QualityGateStatus
from lecturepilot.storage_layout import StorageLayout


def test_concurrent_quality_gate_updates_preserve_every_gate(tmp_path: Path, monkeypatch) -> None:
    store = LearnerStateStore(StorageLayout(tmp_path))
    original_read = learner_state._read_json

    def slow_read(path: Path) -> dict:
        payload = original_read(path)
        time.sleep(0.05)
        return payload

    monkeypatch.setattr(learner_state, "_read_json", slow_read)

    def record(index: int) -> None:
        store.record_quality_gate(
            course_id="course-1",
            lecture_id="lecture-1",
            user_id="student-1",
            decision=QualityGateDecision(
                gate_id=f"gate-{index}",
                status=QualityGateStatus.PASSED,
                reason="test",
            ),
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(record, range(8)))

    path = tmp_path / "users" / store.layout.user_key("student-1")
    payload = json.loads((path / "courses/course-1/lectures/lecture-1/gates.json").read_text())
    assert set(payload["gates"]) == {f"gate-{index}" for index in range(8)}


def test_quality_gate_update_keeps_previous_file_when_atomic_replace_fails(
    tmp_path: Path, monkeypatch
) -> None:
    store = LearnerStateStore(StorageLayout(tmp_path))
    first = QualityGateDecision(
        gate_id="gate-1",
        status=QualityGateStatus.PASSED,
        reason="first",
    )
    store.record_quality_gate(
        course_id="course-1",
        lecture_id="lecture-1",
        user_id="student-1",
        decision=first,
    )
    path = store.layout.user_lecture_root("student-1", "course-1", "lecture-1") / "gates.json"
    original = path.read_bytes()

    def fail_replace(_self: Path, _target: Path) -> Path:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        store.record_quality_gate(
            course_id="course-1",
            lecture_id="lecture-1",
            user_id="student-1",
            decision=QualityGateDecision(
                gate_id="gate-2",
                status=QualityGateStatus.NEEDS_EVIDENCE,
                reason="second",
            ),
        )

    assert path.read_bytes() == original


def test_latest_gate_decisions_reads_only_valid_persisted_decisions(tmp_path: Path) -> None:
    store = LearnerStateStore(StorageLayout(tmp_path))
    path = store.layout.user_lecture_root("student-1", "course-1", "lecture-1") / "gates.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "gates": {
                    "gate-1": {
                        "gate_id": "gate-1",
                        "status": "passed",
                        "reason": "Complete evidence.",
                    },
                    "broken": {"status": "passed"},
                }
            }
        ),
        encoding="utf-8",
    )

    decisions = store.latest_gate_decisions(
        course_id="course-1", lecture_id="lecture-1", user_id="student-1"
    )

    assert list(decisions) == ["gate-1"]
    assert decisions["gate-1"].status == QualityGateStatus.PASSED

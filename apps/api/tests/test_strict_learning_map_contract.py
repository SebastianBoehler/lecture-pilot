import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from lecturepilot.learning_map import (
    LearningMap,
    LearningMapGate,
    read_strict_published_learning_map,
)


def _gate_payload() -> dict:
    return {
        "id": "mechanism-check",
        "concept_id": "mechanism",
        "title": "Mechanism check",
        "prompt": "Explain the mechanism in your own words.",
        "evidence_criteria": [
            {
                "id": "causal-link",
                "description": "Names the cause and its effect.",
                "required": True,
            }
        ],
        "transfer_prompt": "Apply the mechanism to a changed case.",
        "review_after_days": 3,
        "revision": "a" * 64,
        "section_id": "mechanism",
        "source_ref": "lecture.md#mechanism",
    }


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("prompt", ""),
        ("evidence_criteria", []),
        ("transfer_prompt", ""),
        ("review_after_days", None),
        ("revision", None),
    ],
)
def test_learning_map_gate_rejects_incomplete_contract(field: str, replacement: object) -> None:
    payload = _gate_payload()
    if replacement is None:
        payload.pop(field)
    else:
        payload[field] = replacement

    with pytest.raises(ValidationError):
        LearningMapGate.model_validate(payload)


def test_learning_map_rejects_missing_objective_and_revision() -> None:
    payload = {
        "course_id": "course-1",
        "lecture_id": "lecture-1",
        "title": "Lecture",
        "nodes": [],
        "gates": [],
    }

    with pytest.raises(ValidationError):
        LearningMap.model_validate(payload)


def test_learning_map_gate_has_no_evidence_required_compatibility_field() -> None:
    with pytest.raises(ValidationError):
        LearningMapGate.model_validate({**_gate_payload(), "evidence_required": "legacy rubric"})


def test_legacy_generic_learning_map_reads_with_safe_teaching_contract_defaults() -> None:
    payload = {
        "course_id": "course-1",
        "lecture_id": "lecture-1",
        "title": "Lecture",
        "objective": "Apply the mechanism independently.",
        "revision": "043ad5be63817d2ee1f22314639e635d2b30f408f28b9b72e66aa5751210bde2",
        "nodes": [
            {
                "id": "mechanism",
                "title": "Mechanism",
                "lecture_id": "lecture-1",
                "section_id": "mechanism",
                "source_ref": "lecture.md#mechanism",
                "prerequisites": [],
                "gate_ids": ["mechanism-check"],
                "quiz_ids": [],
            }
        ],
        "gates": [
            {
                **_gate_payload(),
                "independent_exit_task": None,
                "practice_target_id": None,
                "revision": "9aac7e6b0f6eca1b9782cdbfe9c1150cc0eb164efd5bfcd64552864fac6480eb",
            }
        ],
    }

    learning_map = LearningMap.model_validate(payload)

    gate = learning_map.gates[0]
    assert gate.target_invariant is None
    assert gate.independent_exit_surface_change is None
    assert gate.delayed_transfer_surface_change is None
    assert gate.misconceptions == []
    assert gate.hint_ladder == []


def test_published_map_rejects_digest_mismatch_without_repair(tmp_path: Path) -> None:
    canvas_dir = tmp_path / "canvas"
    canvas_dir.mkdir()
    payload = {
        "course_id": "course-1",
        "lecture_id": "lecture-1",
        "title": "Lecture",
        "objective": "Apply the mechanism independently.",
        "revision": "b" * 64,
        "nodes": [],
        "gates": [_gate_payload()],
    }
    path = canvas_dir / "learning-map.json"
    original = json.dumps(payload).encode()
    path.write_bytes(original)

    with pytest.raises(ValueError, match="revision"):
        read_strict_published_learning_map(canvas_dir)

    assert path.read_bytes() == original

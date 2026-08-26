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


def _legacy_learning_map_payload() -> dict:
    return {
        "course_id": "course-1",
        "lecture_id": "lecture-1",
        "title": "Lecture",
        "objective": "Apply the mechanism independently.",
        "revision": "2f332450966e4d62ef1881775c75d86f191d63bcbb6d03ed10ac6e9ba923f361",
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
                "revision": "549df79247720520a2f661f39246e7dff613d5329286815a779d03f75d918fdb",
            }
        ],
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


def test_base_schema_learning_map_bytes_read_without_rewriting(tmp_path: Path) -> None:
    payload = _legacy_learning_map_payload()
    canvas_dir = tmp_path / "canvas"
    canvas_dir.mkdir()
    path = canvas_dir / "learning-map.json"
    original = json.dumps(payload, indent=2, sort_keys=True).encode()
    path.write_bytes(original)

    learning_map = read_strict_published_learning_map(canvas_dir)

    assert learning_map is not None
    gate = learning_map.gates[0]
    assert gate.target_invariant is None
    assert gate.independent_exit_task is None
    assert gate.independent_exit_surface_change is None
    assert gate.delayed_transfer_surface_change is None
    assert gate.misconceptions == []
    assert gate.hint_ladder == []
    assert gate.practice_target_id is None
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target_invariant", "Injected teaching contract."),
        ("independent_exit_task", "Injected exit task."),
        ("practice_target_id", None),
    ],
)
def test_legacy_generic_gate_rejects_partial_added_field_with_old_revision(
    field: str,
    value: object,
) -> None:
    payload = _legacy_learning_map_payload()["gates"][0]
    payload[field] = value

    with pytest.raises(ValidationError, match="gate revision"):
        LearningMapGate.model_validate(payload)


def test_legacy_learning_map_rejects_partial_added_gate_field_with_old_revision() -> None:
    payload = _legacy_learning_map_payload()
    payload["gates"][0]["target_invariant"] = "Injected teaching contract."
    payload["gates"][0]["revision"] = (
        "ae55a09bfe33f1355e07e4cb662906cbba7d62f50f75106ef123ba169c4ed6fd"
    )
    payload["revision"] = "2a8261e47b51e664746a49ca1f786b7551503530474e0571680b4aecae585bd3"

    with pytest.raises(ValidationError, match="revision"):
        LearningMap.model_validate(payload)


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

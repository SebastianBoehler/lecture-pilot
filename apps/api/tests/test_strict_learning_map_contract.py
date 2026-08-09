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

import json
from pathlib import Path

import pytest

from auth_helpers import professor_headers
from test_practice_design_routes import _client, _design_path, _proposal_path, _Planner


@pytest.mark.parametrize("identity", ["target", "criterion", "misconception"])
def test_put_rejects_stable_id_mutation_and_preserves_the_stored_design(
    tmp_path: Path, identity: str
) -> None:
    client = _client(tmp_path)
    client.app.state.practice_design_planner = _Planner()
    design = client.post(_proposal_path(), headers=professor_headers()).json()
    targets = design["targets"]
    if identity == "target":
        targets[0]["id"] = "renamed-target"
    elif identity == "criterion":
        targets[0]["evidence_criteria"][0]["id"] = "renamed-criterion"
    else:
        targets[0]["misconceptions"] = [
            {
                "id": "new-misconception",
                "description": "Uses an unsupported shortcut.",
                "diagnostic_cue": "The response skips the source-grounded reason.",
            }
        ]

    response = client.put(
        _design_path(), headers=professor_headers(), json=_update_payload(design, targets)
    )

    assert response.status_code == 422
    assert "Stable practice design IDs" in response.json()["detail"]
    stored = client.get(_design_path(), headers=professor_headers()).json()
    assert stored["revision"] == design["revision"]
    assert stored["targets"][0]["id"] == "posterior"
    assert stored["targets"][0]["evidence_criteria"][0]["id"] == "substitute"
    assert stored["targets"][0]["misconceptions"] == []


def test_put_maps_an_absent_design_to_not_found(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.practice_design_planner = _Planner()
    design = client.post(_proposal_path(), headers=professor_headers()).json()
    path = client.app.state.canvas_workspace.layout.lecture_practice_design_path(
        design["course_id"], design["lecture_id"]
    )
    path.unlink()

    response = client.put(
        _design_path(), headers=professor_headers(), json=_update_payload(design, design["targets"])
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Practice design has not been proposed."


def test_put_maps_corrupt_storage_to_a_safe_integrity_error(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.practice_design_planner = _Planner()
    design = client.post(_proposal_path(), headers=professor_headers()).json()
    path = client.app.state.canvas_workspace.layout.lecture_practice_design_path(
        design["course_id"], design["lecture_id"]
    )
    path.write_text(json.dumps({"private_detail": "do not expose"}), encoding="utf-8")

    response = client.put(
        _design_path(), headers=professor_headers(), json=_update_payload(design, design["targets"])
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Stored practice design failed an integrity check."
    assert "private_detail" not in response.text


def _update_payload(design: dict, targets: list[dict]) -> dict:
    return {
        "source_revision": design["source_revision"],
        "practice_design_revision": design["revision"],
        "lecture_title": design["lecture_title"],
        "objective": "A permitted content edit.",
        "targets": targets,
    }

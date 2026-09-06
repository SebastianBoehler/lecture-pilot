from datetime import timedelta

import pytest

from auth_helpers import professor_headers, student_headers
from lecturepilot.coaching_goal_evidence import GoalEvidence
from lecturepilot.coaching_state_models import CoachingProgress, PendingCheck
from lecturepilot.learner_lesson_state import _goal_evidence
from practice_gate_coaching_test_helpers import IDS, NOW, bank_gate
from test_learner_lesson_state_routes import _client, COURSE_ID

SAFE_GATE_FIELDS = {"id", "concept_id", "title", "revision", "section_id"}


@pytest.mark.parametrize(
    "headers", [student_headers("student-a", course_ids=[COURSE_ID]), professor_headers()]
)
def test_learning_map_http_excludes_hidden_assessments_without_mutating_publication(
    tmp_path, headers
):
    client = _client(tmp_path)
    store = client.app.state.canvas_workspace.course_canvas_store
    map_path = store.path(COURSE_ID, "lecture-open") / "learning-map.json"
    before = map_path.read_bytes()
    full = store.learning_map(course_id=COURSE_ID, lecture_id="lecture-open")
    response = client.get(
        f"/courses/{COURSE_ID}/lectures/lecture-open/learning-map", headers=headers
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["revision"] == full.revision
    assert [g["revision"] for g in payload["gates"]] == [g.revision for g in full.gates]
    assert all(set(gate) == SAFE_GATE_FIELDS for gate in payload["gates"])
    assert map_path.read_bytes() == before


@pytest.mark.parametrize("stage", ["independent_exit", "delayed_transfer"])
def test_focused_state_hides_missing_evidence_on_server_without_discarding_history(stage):
    gate = bank_gate()
    progress = CoachingProgress.empty(course_id=IDS["course_id"], lecture_id=IDS["lecture_id"])
    progress.goal_evidence[f"{gate.id}@{gate.revision}"] = GoalEvidence(
        gate_id=gate.id,
        gate_revision=gate.revision,
        supported=True,
        missing_evidence_ids=[gate.evidence_criteria[0].id],
    )
    visible = _goal_evidence(progress, [gate])[0]
    assert visible.missing_evidence == [gate.evidence_criteria[0].description]
    task = next(task for task in gate.supplemental_tasks if task.stage == stage)
    progress.pending_check = PendingCheck(
        gate_id=gate.id,
        gate_revision=gate.revision,
        prompt=task.prompt,
        assistance_level="none",
        assistance_content=None,
        kind="delayed_transfer" if stage == "delayed_transfer" else "standard",
        stage=stage,
        issued_at=NOW + timedelta(minutes=1),
        task_id=task.id,
    )
    before = progress.model_dump_json()
    hidden = _goal_evidence(progress, [gate])[0]
    assert hidden.missing_evidence_ids == []
    assert hidden.missing_evidence == []
    assert hidden.supported
    assert progress.model_dump_json() == before


def test_navigation_projection_omits_entire_supplemental_bank_and_rubric():
    from lecturepilot.learner_learning_map import learner_learning_map
    from lecturepilot.learning_map import LearningMap

    gate = bank_gate()
    full = LearningMap.create(
        course_id=IDS["course_id"],
        lecture_id=IDS["lecture_id"],
        title="Mechanism",
        objective="Apply the boundary.",
        gates=[gate],
        nodes=[
            dict(
                id="mechanism",
                title="Mechanism",
                lecture_id=IDS["lecture_id"],
                section_id=gate.section_id,
                prerequisites=[],
                gate_ids=[gate.id],
                quiz_ids=[],
            )
        ],
    )
    before = full.model_dump_json()
    safe = learner_learning_map(full)
    assert set(safe.gates[0].model_dump()) == SAFE_GATE_FIELDS
    assert all(task.prompt not in safe.model_dump_json() for task in gate.supplemental_tasks)
    assert gate.evidence_criteria[0].description not in safe.model_dump_json()
    assert safe.revision == full.revision
    assert safe.gates[0].revision == gate.revision
    assert full.model_dump_json() == before

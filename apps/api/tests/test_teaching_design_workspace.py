import json

import pytest

from lecturepilot.course_learning_intent import LearningGoal, LearningIntent, digest, goal_for
from lecturepilot.practice_evidence_catalogue import compact_evidence_anchors, evidence_catalogue
from lecturepilot.teaching_design_workspace import TeachingDesignWorkspace
from practice_design_test_helpers import proposal, target
from reviewed_task_bank_helpers import with_bank
from test_practice_design_semantic_review import _source


@pytest.fixture
def workspace(tmp_path):
    source = _source()
    original = with_bank(
        target(source_refs=("lecture-01.md",), source_excerpt=source.sections[0].blocks[0].text)
    )
    sibling = original.model_copy(update={"id": "another-goal"})
    design = proposal().model_copy(update={"targets": (original, sibling)})
    payload = dict(
        source_revision="a" * 64,
        objective=design.objective,
        planning_context=design.planning_context.model_dump(mode="json"),
        goals=[goal_for(t).model_dump(mode="json") for t in design.targets],
        fixed_targets=[{"id": sibling.id, "revision": digest(sibling.model_dump(mode="json"))}],
    )
    intent = LearningIntent.model_validate({**payload, "revision": digest(payload)})
    return TeachingDesignWorkspace(
        root=tmp_path,
        source=source,
        intent=intent,
        initial=design,
        catalogue=evidence_catalogue(source, ("lecture-01.md",)),
        paths=("lecture-01.md",),
        authorize=lambda: None,
    )


def teaching(workspace, key="derive-conclusion"):
    wire = compact_evidence_anchors(workspace.targets[key], workspace.catalogue)
    wire.pop("source_refs")
    for name in LearningGoal.model_fields:
        if name != "id":
            wire.pop(name)
    return wire


def test_write_keeps_sibling_fixed_tasks_and_all_approved_fields(workspace):
    before = workspace.proposal()
    wire = teaching(workspace)
    wire["baseline_task"] = "Explain how the supplied evidence supports your conclusion."
    assert workspace.write(**wire)["saved"]
    after = workspace.proposal()
    workspace.intent.require_matches(after)
    assert after.targets[1] == before.targets[1]
    assert after.targets[0].baseline_task != before.targets[0].baseline_task
    assert [t.id for t in after.targets] == [t.id for t in before.targets]


@pytest.mark.parametrize("change", ["unknown", "fixed", "goal", "source", "bank"])
def test_invalid_write_does_not_replace_existing_draft(workspace, change):
    before = workspace.proposal()
    wire = teaching(workspace, "another-goal" if change == "fixed" else "derive-conclusion")
    if change == "unknown":
        wire["id"] = "invented"
    if change == "goal":
        wire["outcome"] = "Replace the approved outcome."
    if change == "source":
        wire["baseline_anchor"] = "nonexistent-evidence"
    if change == "bank":
        wire["supplemental_tasks"] = []
    result = workspace.write(**wire)
    assert not result["saved"], result
    assert workspace.proposal() == before
    if (workspace.root / "draft.json").exists():
        assert (
            json.loads((workspace.root / "draft.json").read_text())["targets"] == workspace.targets
        )

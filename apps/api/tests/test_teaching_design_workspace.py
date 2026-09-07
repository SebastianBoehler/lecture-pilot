import json

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.course_practice_design_review_models import PracticeDesignReviewResult
from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.teaching_design_job import TeachingDesignJob, run_teaching_design_job
from practice_design_test_helpers import passing_review

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


def test_edit_repairs_one_text_span_without_rewriting_siblings(workspace):
    wire = teaching(workspace)
    wire["baseline_task"] = "Use the supplied comparison with K=1:84 and K=2:4."
    assert workspace.write(**wire)["saved"]
    before = workspace.proposal()
    assert workspace.edit("derive-conclusion", "K=1:84", "K=1:88")["saved"]
    after = workspace.proposal()
    assert after.targets[0].baseline_task == "Use the supplied comparison with K=1:88 and K=2:4."
    assert (
        after.targets[0].model_copy(update={"baseline_task": before.targets[0].baseline_task})
        == before.targets[0]
    )
    assert after.targets[1] == before.targets[1]
    workspace.intent.require_matches(after)


@pytest.mark.parametrize("change", ["missing", "ambiguous", "goal", "fixed", "invalid"])
def test_edit_rejects_unsafe_changes_without_mutating_draft(workspace, change):
    wire = teaching(workspace)
    wire["baseline_task"] = "A unique calculation with repeated repeated terms."
    assert workspace.write(**wire)["saved"]
    before = workspace.proposal()
    key, old, new = "derive-conclusion", "not-present", "replacement"
    if change == "ambiguous":
        old = "repeated"
    elif change == "goal":
        old = workspace.goals[key].outcome
    elif change == "fixed":
        key, old = "another-goal", workspace.targets["another-goal"]["baseline_task"]
    elif change == "invalid":
        old, new = wire["baseline_task"], ""
    assert not workspace.edit(key, old, new)["saved"]
    assert workspace.proposal() == before


@pytest.mark.asyncio
async def test_failed_review_requires_an_edit_before_another_validation(workspace):
    original = workspace.proposal()
    reviews = 0
    calls = 0

    async def review(proposal):
        nonlocal reviews
        reviews += 1
        result = passing_review()
        if reviews == 1:
            checks = list(result.checks)
            checks[1] = checks[1].model_copy(
                update={
                    "severity": "warning",
                    "summary": "Ask for an explicit explanation in the baseline.",
                    "target_ids": (original.targets[0].id,),
                    "supporting_anchors": (original.targets[0].outcome_anchor,),
                }
            )
            return PracticeDesignReviewResult(checks=tuple(checks))
        return result

    def model(messages, info):
        nonlocal calls
        names = {tool.name for tool in info.function_tools}
        calls += 1
        if calls == 1:
            assert "validate" in names
            return ModelResponse(parts=[ToolCallPart("validate", {})])
        if calls == 2:
            assert "validate" not in names
            assert "edit" in names
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "edit",
                        {
                            "target_id": original.targets[0].id,
                            "old_text": original.targets[0].baseline_task,
                            "new_text": original.targets[0].baseline_task
                            + " Explain your reasoning explicitly.",
                        },
                    )
                ]
            )
        if calls == 3:
            assert "validate" in names
            return ModelResponse(parts=[ToolCallPart("validate", {})])
        return ModelResponse(parts=[ToolCallPart("final_result", {"ready": True})])

    job = TeachingDesignJob(
        root=workspace.root / "agent",
        source=workspace.source,
        intent=workspace.intent,
        initial=original,
        paths=workspace.paths,
        source_revision="a" * 64,
        settings=ProviderSettings(
            provider="openai",
            model="openai/test",
            api_key_env="OPENAI_API_KEY",
            capabilities={ProviderCapability.CHAT, ProviderCapability.TOOL_CALLS},
        ),
        review=review,
        authorize=lambda: None,
    )
    changed, result = await run_teaching_design_job(job, model=FunctionModel(model))
    assert reviews == 2
    assert calls == 4
    assert changed.targets[1] == original.targets[1]
    workspace.intent.require_matches(changed)
    metrics = json.loads((job.root / "session.json").read_text())["metrics"]
    assert metrics["repair_edits"] == 1


def test_edit_identifies_protected_goal_text_instead_of_retrying_missing_span(workspace):
    goal = workspace.goals["derive-conclusion"]
    result = workspace.edit(goal.id, goal.target_invariant, "Different invariant")
    assert not result["saved"]
    assert result["error_code"] == "approved_intent_read_only"
    assert "target_invariant" in result["protected_fields"]

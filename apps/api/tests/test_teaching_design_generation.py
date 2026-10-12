import json
import pytest
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.course_learning_intent import LearningIntent, digest, goal_for
from lecturepilot.course_practice_design_review_models import PracticeDesignReviewResult
from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.practice_evidence_catalogue import evidence_catalogue
from lecturepilot.teaching_design_job import TeachingDesignJob, run_teaching_design_job
from lecturepilot.teaching_design_workspace import TeachingDesignWorkspace
from practice_design_review_test_helpers import passing_review
from practice_design_test_helpers import proposal, target
from reviewed_task_bank_helpers import with_bank
from test_practice_design_semantic_review import _source
from test_teaching_design_workspace import teaching

SETTINGS = ProviderSettings(
    provider="openai",
    model="openai/test",
    api_key_env="OPENAI_API_KEY",
    capabilities={ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON},
)


@pytest.fixture
def setup(tmp_path):
    source = _source()
    first = with_bank(
        target(source_refs=("lecture-01.md",), source_excerpt=source.sections[0].blocks[0].text)
    )
    design = proposal().model_copy(
        update={"targets": (first, first.model_copy(update={"id": "another-goal"}))}
    )
    payload = dict(
        source_revision="a" * 64,
        objective=design.objective,
        planning_context=design.planning_context.model_dump(mode="json"),
        goals=[goal_for(t).model_dump(mode="json") for t in design.targets],
        fixed_targets=[],
    )
    intent = LearningIntent.model_validate({**payload, "revision": digest(payload)})
    reference = TeachingDesignWorkspace(
        root=tmp_path / "reference",
        source=source,
        intent=intent,
        initial=design,
        catalogue=evidence_catalogue(source, ("lecture-01.md",)),
        paths=("lecture-01.md",),
        authorize=lambda: None,
    )
    wires = {goal: teaching(reference, goal) for goal in reference.goals}
    return source, intent, wires, first.outcome_anchor


def flagged(goal_id, anchor):
    checks = list(passing_review().checks)
    checks[1] = checks[1].model_copy(
        update={
            "severity": "critical",
            "summary": "The baseline does not elicit the outcome.",
            "target_ids": (goal_id,),
            "supporting_anchors": (anchor,),
        }
    )
    return PracticeDesignReviewResult(checks=tuple(checks))


def run(tmp_path, source, intent, model, review):
    job = TeachingDesignJob(
        root=tmp_path / "job",
        source=source,
        intent=intent,
        initial=None,
        paths=("lecture-01.md",),
        source_revision="a" * 64,
        settings=SETTINGS,
        review=review,
        authorize=lambda: None,
    )
    return run_teaching_design_job(job, model=FunctionModel(model))


def responder(wires, calls, invalid_first=()):
    def model(messages, info):
        schema = info.model_request_parameters.output_object.json_schema
        goal_id = schema["properties"]["id"]["enum"][0]
        prompt = str(messages[0].parts[-1].content)
        calls.append(("repair" if "Repair the teaching" in prompt else "write", goal_id))
        wire = dict(wires[goal_id])
        if goal_id in invalid_first and calls.count(("write", goal_id)) == 1:
            wire["supplemental_tasks"] = []
        return ModelResponse(parts=[TextPart(json.dumps(wire))])

    return model


@pytest.mark.asyncio
async def test_each_goal_is_written_once_and_reviewed_once(tmp_path, setup):
    source, intent, wires, anchor = setup
    calls, reviews = [], []

    async def review(proposal):
        reviews.append(proposal)
        return passing_review()

    result, checked = await run(tmp_path, source, intent, responder(wires, calls), review)
    assert sorted(calls) == [("write", "another-goal"), ("write", "derive-conclusion")]
    assert len(reviews) == 1
    intent.require_matches(result)
    assert checked == passing_review()


@pytest.mark.asyncio
async def test_invalid_teaching_is_retried_by_deterministic_validation(tmp_path, setup):
    source, intent, wires, anchor = setup
    calls = []

    async def review(proposal):
        return passing_review()

    result, _ = await run(
        tmp_path, source, intent, responder(wires, calls, {"derive-conclusion"}), review
    )
    assert calls.count(("write", "derive-conclusion")) == 2
    intent.require_matches(result)


@pytest.mark.asyncio
async def test_unresolved_findings_are_repaired_once_then_kept_as_warnings(tmp_path, setup):
    source, intent, wires, anchor = setup
    calls, reviews = [], []

    async def review(proposal):
        reviews.append(proposal)
        return flagged("derive-conclusion", anchor)

    result, checked = await run(tmp_path, source, intent, responder(wires, calls), review)
    assert calls.count(("repair", "derive-conclusion")) == 1
    assert ("repair", "another-goal") not in calls
    # The repair is not re-reviewed: its finding stays a warning, labelled truthfully.
    assert len(reviews) == 1
    critical = [check for check in checked.checks if check.severity == "critical"]
    assert [check.summary for check in critical] == [
        "Repaired once, not re-checked: The baseline does not elicit the outcome."
    ]
    intent.require_matches(result)

    calls.clear()
    await run(tmp_path, source, intent, responder(wires, calls), review)
    assert calls == []
    assert len(reviews) == 1


@pytest.mark.asyncio
async def test_design_conflict_repairs_only_the_named_goal_without_a_new_review(tmp_path, setup):
    source, intent, wires, anchor = setup
    calls, reviews = [], []

    async def review(proposal):
        reviews.append(proposal)
        return passing_review()

    current, _ = await run(tmp_path, source, intent, responder(wires, calls), review)
    calls.clear()
    # The current implementation was reviewed once (its earlier repair is spent); a verified
    # canvas design conflict names one checkpoint and gets exactly one targeted repair.
    job = TeachingDesignJob(
        root=tmp_path / "conflict",
        source=source,
        intent=intent,
        initial=current,
        initial_review=flagged("derive-conclusion", anchor),
        paths=("lecture-01.md",),
        source_revision="a" * 64,
        settings=SETTINGS,
        review=review,
        authorize=lambda: None,
        repair_context="practice-another-goal: the approved task omits the rubric's rule.",
    )
    result, checked = await run_teaching_design_job(
        job, model=FunctionModel(responder(wires, calls))
    )
    assert calls == [("repair", "another-goal")]
    assert len(reviews) == 1
    assert checked == flagged("derive-conclusion", anchor)
    intent.require_matches(result)


@pytest.mark.asyncio
async def test_interrupted_repairs_resume_without_a_second_review(tmp_path, setup):
    source, intent, wires, anchor = setup
    calls, reviews = [], []

    async def review(proposal):
        reviews.append(proposal)
        checks = list(flagged("derive-conclusion", anchor).checks)
        checks[1] = checks[1].model_copy(
            update={"target_ids": ("derive-conclusion", "another-goal")}
        )
        return PracticeDesignReviewResult(checks=tuple(checks))

    def interrupted(messages, info):
        if "Repair the teaching for goal ID another-goal" in str(messages[0].parts[-1].content):
            raise RuntimeError("provider disconnected")
        return responder(wires, calls)(messages, info)

    with pytest.raises(RuntimeError, match="provider disconnected"):
        await run(tmp_path, source, intent, interrupted, review)
    assert calls.count(("repair", "derive-conclusion")) == 1

    calls.clear()
    await run(tmp_path, source, intent, responder(wires, calls), review)
    assert calls == [("repair", "another-goal")]
    assert len(reviews) == 1

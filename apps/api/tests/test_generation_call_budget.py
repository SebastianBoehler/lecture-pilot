"""Pin model calls per stage for a four-goal lecture (canvas: test_authoring_call_budget.py).

Goals:    happy 2 (proposal + support review), worst 3 (+ one repair; was 4 with a re-review).
Teaching: happy 5 (4 goals + review), worst 9 (+ 4 repairs; was 10 with an annotating review);
          a canvas design conflict adds exactly one repair per named goal and no review.
"""

import pytest
from pydantic_ai.models.function import FunctionModel

from lecturepilot.course_learning_intent import LearningIntent, digest, goal_for
from lecturepilot.course_practice_design_review_models import PracticeDesignReviewResult
from lecturepilot.practice_evidence_catalogue import evidence_catalogue
from lecturepilot.teaching_design_job import TeachingDesignJob, run_teaching_design_job
from lecturepilot.teaching_design_workspace import TeachingDesignWorkspace
from auth_helpers import professor_headers
from practice_design_review_test_helpers import passing_review
from practice_design_route_test_helpers import design_path
from practice_design_test_helpers import proposal, target
from reviewed_task_bank_helpers import with_bank
from test_learning_intent_routes import goal_client
from test_practice_design_semantic_review import _source
from test_teaching_design_generation import SETTINGS, responder
from test_teaching_design_workspace import teaching

GOALS = [f"goal-{n}" for n in range(1, 5)]


@pytest.mark.parametrize("flagged, expected", [((), 2), (tuple(f"goal-{n}" for n in range(4)), 3)])
def test_goal_stage_budget(tmp_path, flagged, expected):
    api, calls = goal_client(tmp_path, goal_count=4, findings=(flagged,))
    response = api.post(design_path() + "/intent/proposal", headers=professor_headers())
    assert response.status_code == 200, response.text
    assert len(calls) == expected


@pytest.fixture
def four_goals(tmp_path):
    source = _source()
    first = with_bank(
        target(source_refs=("lecture-01.md",), source_excerpt=source.sections[0].blocks[0].text)
    )
    design = proposal().model_copy(
        update={"targets": tuple(first.model_copy(update={"id": goal}) for goal in GOALS)}
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


def review_flagging(goals, anchor):
    checks = list(passing_review().checks)
    if goals:
        checks[1] = checks[1].model_copy(
            update={
                "severity": "critical",
                "summary": "The baseline does not elicit the outcome.",
                "target_ids": tuple(goals),
                "supporting_anchors": (anchor,),
            }
        )
    return PracticeDesignReviewResult(checks=tuple(checks))


def job(root, source, intent, review, **changes):
    arguments = dict(
        root=root,
        source=source,
        intent=intent,
        initial=None,
        paths=("lecture-01.md",),
        source_revision="a" * 64,
        settings=SETTINGS,
        review=review,
        authorize=lambda: None,
    )
    return TeachingDesignJob(**{**arguments, **changes})


@pytest.mark.asyncio
@pytest.mark.parametrize("flagged, expected", [((), 5), (tuple(GOALS), 9)])
async def test_teaching_stage_budget(tmp_path, four_goals, flagged, expected):
    source, intent, wires, anchor = four_goals
    calls, reviews = [], []

    async def review(proposal):
        reviews.append(proposal)
        return review_flagging(flagged, anchor)

    current, checked = await run_teaching_design_job(
        job(tmp_path / "job", source, intent, review), model=FunctionModel(responder(wires, calls))
    )
    assert len(calls) + len(reviews) == expected
    assert len(reviews) == 1

    # A verified canvas design conflict on one checkpoint: one repair, no further review.
    calls.clear()
    await run_teaching_design_job(
        job(
            tmp_path / "conflict",
            source,
            intent,
            review,
            initial=current,
            initial_review=checked,
            repair_context="practice-goal-3: the approved task omits the rubric's rule.",
        ),
        model=FunctionModel(responder(wires, calls)),
    )
    assert calls == [("repair", "goal-3")]
    assert len(reviews) == 1

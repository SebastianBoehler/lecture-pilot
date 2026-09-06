from reviewed_task_bank_helpers import with_bank
import json

import pytest

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.course_practice_design_planner import PracticeDesignPlanner
from lecturepilot.practice_evidence_catalogue import compact_evidence_anchors, evidence_catalogue
from practice_design_test_helpers import proposal, target
from test_practice_design_semantic_review import _Registry, _review_payload, _source


@pytest.mark.parametrize("severity", ["critical", "warning"])
async def test_proposal_repairs_rubric_before_returning_for_approval(severity):
    source = _source()
    catalogue = evidence_catalogue(source, ("lecture-01.md",))
    draft = proposal().model_dump(mode="json")
    draft["targets"] = [
        with_bank(
            target(source_refs=("lecture-01.md",), source_excerpt=source.sections[0].blocks[0].text)
        ).model_dump(mode="json")
    ]
    draft["targets"][0]["evidence_criteria"][0]["description"] = "Accept only the example answer."
    wire = compact_evidence_anchors(draft, catalogue)
    wire["targets"][0].pop("source_refs")
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        if calls > 1:
            assert "Rejecting other justified conclusions" in str(messages)
            wire["targets"][0]["evidence_criteria"][0]["description"] = (
                "Accept any conclusion justified by the supplied evidence."
            )
        return ModelResponse(parts=[TextPart(json.dumps(wire))])

    class Critic:
        async def complete_review(self, *, messages, **kwargs):
            review = _review_payload()
            if "Accept only the example answer" in messages[1]["content"]:
                review["checks"][6].update(
                    severity=severity,
                    summary="Rejecting other justified conclusions contradicts the outcome.",
                    target_ids=["derive-conclusion"],
                    supporting_anchors=[{"source_path": "lecture-01.md", "excerpt": "evidence"}],
                )
            return review

    planner = PracticeDesignPlanner(
        provider_registry=_Registry(), model=FunctionModel(respond), review_client=Critic()
    )
    result = await planner.propose(
        source=source, source_revision="a" * 64, allowed_source_paths=("lecture-01.md",)
    )
    assert result.proposal.targets[0].evidence_criteria[0].description == (
        "Accept any conclusion justified by the supplied evidence."
    )
    assert all(check.severity == "pass" for check in result.review.checks)


async def test_repair_cannot_change_the_existing_learning_objective():
    source = _source()
    initial = proposal().model_copy(
        update={
            "targets": (
                with_bank(
                    target(
                        source_refs=("lecture-01.md",),
                        source_excerpt=source.sections[0].blocks[0].text,
                    )
                ),
            )
        }
    )
    catalogue = evidence_catalogue(source, ("lecture-01.md",))
    wire = compact_evidence_anchors(initial.model_dump(mode="json"), catalogue)
    wire["targets"][0].pop("source_refs")
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        wire["objective"] = "Name the word evidence." if calls == 1 else initial.objective
        if calls > 1:
            assert "Preserve the existing objective" in str(messages)
        return ModelResponse(parts=[TextPart(json.dumps(wire))])

    class Critic:
        async def complete_review(self, **kwargs):
            return _review_payload()

    planner = PracticeDesignPlanner(
        provider_registry=_Registry(), model=FunctionModel(respond), review_client=Critic()
    )
    result = await planner.propose(
        source=source,
        source_revision="a" * 64,
        allowed_source_paths=("lecture-01.md",),
        initial=initial,
    )
    assert result.proposal.objective == initial.objective
    assert result.proposal.targets[0].outcome == initial.targets[0].outcome

import json

import pytest
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.course_learning_intent import LearningGoal, LearningIntent, goal_for, digest
from lecturepilot.course_practice_design_planner import PracticeDesignPlanner
from lecturepilot.practice_evidence_catalogue import compact_evidence_anchors, evidence_catalogue
from practice_design_test_helpers import proposal, target
from reviewed_task_bank_helpers import with_bank
from test_practice_design_semantic_review import _Registry, _source, _review_payload


@pytest.mark.parametrize("wrong_id", [False, True])
async def test_approved_goal_fields_are_backend_owned(wrong_id):
    source = _source()
    design = proposal().model_copy(
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
    payload = dict(
        source_revision="a" * 64,
        objective=design.objective,
        planning_context=design.planning_context.model_dump(mode="json"),
        goals=[goal_for(t).model_dump(mode="json") for t in design.targets],
        fixed_targets=[],
    )
    intent = LearningIntent.model_validate({**payload, "revision": digest(payload)})
    wire = compact_evidence_anchors(
        design.model_dump(mode="json"), evidence_catalogue(source, ("lecture-01.md",))
    )
    wire.pop("objective")
    wire.pop("planning_context")
    for item in wire["targets"]:
        item.pop("source_refs")
        for field in LearningGoal.model_fields:
            if field != "id":
                item.pop(field)
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        schema = info.model_request_parameters.output_object.json_schema
        assert "objective" not in schema["properties"]
        properties = schema["properties"]["targets"]["items"]["properties"]
        assert "outcome" not in properties
        assert properties["id"]["enum"] == [intent.goals[0].id]
        wire["targets"][0]["id"] = (
            "invented-goal" if wrong_id and calls == 1 else intent.goals[0].id
        )
        if calls > 1:
            assert "approved goal IDs in their original order" in str(messages)
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
        protected_intent=intent,
    )
    intent.require_matches(result.proposal)
    assert calls == (2 if wrong_id else 1)

import json

import pytest

from lecturepilot.course_learning_intent import LearningGoal, LearningIntent, goal_for, digest
from lecturepilot.practice_evidence_catalogue import compact_evidence_anchors, evidence_catalogue
from practice_design_test_helpers import proposal, target
from reviewed_task_bank_helpers import with_bank
from test_practice_design_semantic_review import _source


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
    from lecturepilot.protected_teaching_output import bind_approved_intent, teaching_output_schema
    from lecturepilot.course_practice_design_prompt import practice_design_response_format
    from lecturepilot.practice_evidence_catalogue import expand_evidence_ids
    from lecturepilot.course_practice_design_models import PracticeDesignProposal

    catalogue = evidence_catalogue(source, ("lecture-01.md",))
    schema = teaching_output_schema(
        practice_design_response_format(catalogue)["json_schema"]["schema"], intent
    )
    assert "objective" not in schema["properties"]
    properties = schema["$defs"]["PracticeTarget"]["properties"]
    assert "outcome" not in properties
    assert properties["id"]["enum"] == [intent.goals[0].id]
    if wrong_id:
        wire["targets"][0]["id"] = "invented-goal"
        with pytest.raises(ValueError, match="approved goal IDs"):
            bind_approved_intent(wire, intent)
        wire["targets"][0]["id"] = intent.goals[0].id
    hydrated = expand_evidence_ids(wire, catalogue, derive_source_refs=True)
    result = PracticeDesignProposal.model_validate_json(
        json.dumps(bind_approved_intent(hydrated, intent))
    )
    intent.require_matches(result)

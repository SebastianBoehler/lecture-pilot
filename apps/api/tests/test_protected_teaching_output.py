from lecturepilot.learning_design.course_learning_intent import LearningIntent, goal_for, digest
from lecturepilot.learning_design.course_practice_design_prompt import (
    practice_design_response_format,
)
from lecturepilot.learning_design.practice_evidence_catalogue import evidence_catalogue
from lecturepilot.authoring.protected_teaching_output import teaching_output_schema
from practice_design_test_helpers import proposal, target
from reviewed_task_bank_helpers import with_bank
from test_practice_design_semantic_review import _source


def test_approved_goal_fields_are_backend_owned_in_the_teaching_schema():
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
    catalogue = evidence_catalogue(source, ("lecture-01.md",))

    schema = teaching_output_schema(
        practice_design_response_format(catalogue)["json_schema"]["schema"], intent
    )

    assert "objective" not in schema["properties"]
    properties = schema["$defs"]["PracticeTarget"]["properties"]
    assert "outcome" not in properties
    assert properties["id"]["enum"] == [intent.goals[0].id]

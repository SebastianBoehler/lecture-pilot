"""Compile AI teaching details around immutable professor-approved intent."""

from copy import deepcopy

from lecturepilot.course_learning_intent import LearningGoal, LearningIntent
from lecturepilot.practice_evidence_catalogue import hydrate_source_refs


def teaching_output_schema(schema: dict, intent: LearningIntent | None) -> dict:
    if intent is None:
        return schema
    schema = deepcopy(schema)
    for field in ("objective", "planning_context"):
        schema["properties"].pop(field)
        schema["required"].remove(field)
    target = schema["$defs"]["PracticeTarget"]
    for field in LearningGoal.model_fields:
        if field != "id":
            target["properties"].pop(field)
            target["required"].remove(field)
    target["properties"]["id"] = {"type": "string", "enum": [goal.id for goal in intent.goals]}
    return schema


def bind_approved_intent(output: dict, intent: LearningIntent | None) -> dict:
    if intent is None:
        return output
    targets = output.get("targets", [])
    if [target.get("id") for target in targets] != [goal.id for goal in intent.goals]:
        raise ValueError(
            "Return all approved goal IDs in their original order; do not omit or add goals."
        )
    bound = {
        **output,
        "objective": intent.objective,
        "planning_context": intent.planning_context.model_dump(mode="json"),
        "targets": [
            {**target, **goal.model_dump(mode="json")}
            for target, goal in zip(targets, intent.goals, strict=True)
        ],
    }
    hydrate_source_refs(bound)
    return bound

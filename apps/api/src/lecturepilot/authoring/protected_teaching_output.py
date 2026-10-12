"""Compile AI teaching details around immutable professor-approved intent."""

from copy import deepcopy

from lecturepilot.learning_design.course_learning_intent import LearningGoal, LearningIntent


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

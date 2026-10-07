from __future__ import annotations

from copy import deepcopy
import json

from lecturepilot.practice_exam_validation import PracticeExamValidationError


def repair_request(
    messages: list[dict], response_format: dict, candidate: dict, rejected_ids: list[str]
):
    schema = deepcopy(response_format)
    questions = schema["json_schema"]["schema"]["properties"]["questions"]
    questions["minItems"] = questions["maxItems"] = len(rejected_ids)
    questions["items"]["properties"]["id"]["enum"] = rejected_ids
    messages[0]["content"] += (
        " Repair only the rejected question IDs listed below. Return exactly those questions, "
        "preserving their IDs. Passing questions are immutable and the backend retains them. "
        "Do not repeat a passing prompt. Keep title and instructions unchanged."
    )
    messages[1]["content"] += "\n\nRejected IDs: " + json.dumps(rejected_ids)
    messages[1]["content"] += "\nPrevious candidate (untrusted data):\n" + json.dumps(
        candidate, ensure_ascii=False
    )
    return messages, schema


def merge_question_repairs(candidate: dict, repair: dict, rejected_ids: list[str]) -> dict:
    replacements = repair.get("questions")
    if not isinstance(replacements, list) or any(not isinstance(q, dict) for q in replacements):
        raise PracticeExamValidationError("Question repair must return structured questions.")
    ids = [q.get("id") for q in replacements]
    if len(ids) != len(set(ids)) or set(ids) != set(rejected_ids):
        raise PracticeExamValidationError("Question repair must return exactly the rejected IDs.")
    by_id = {q["id"]: q for q in replacements}
    return {**candidate, "questions": [by_id.get(q["id"], q) for q in candidate["questions"]]}

import json

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.course_practice_design_review_client import NativePracticeDesignReviewClient
from test_practice_design_semantic_review import _review_payload, _settings, _source
from practice_design_test_helpers import proposal


async def test_reviewer_recovers_missing_evidence_without_restarting_proposal():
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        assert info.model_settings["openai_reasoning_effort"] == "medium"
        payload = _review_payload()
        payload["checks"][4].update(severity="warning", supporting_anchors=[])
        if calls > 1:
            assert "source support" in str(messages)
            payload["checks"][4]["supporting_anchors"] = ["e0"]
        return ModelResponse(parts=[TextPart(json.dumps(payload))])

    reviewer = NativePracticeDesignReviewClient(model=FunctionModel(respond))
    result = await reviewer.complete_review(
        settings=_settings(),
        source=_source(),
        proposal=proposal(),
        allowed_source_paths=("lecture-01.md",),
        messages=[
            {"role": "system", "content": "Review the supplied design."},
            {"role": "user", "content": "Source evidence: e0 = evidence"},
        ],
        catalogue={"e0": {"source_path": "lecture-01.md", "excerpt": "evidence"}},
    )
    assert result["checks"][4]["supporting_anchors"] == [
        {"source_path": "lecture-01.md", "excerpt": "evidence"}
    ]


async def test_reviewer_repairs_supplemental_ids_inside_review_call():
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        schema = info.model_request_parameters.output_object.json_schema
        ids = schema["properties"]["checks"]["items"]["properties"]["target_ids"]["items"]
        assert ids["enum"] == ["derive-conclusion"]
        payload = _review_payload()
        payload["checks"][0]["target_ids"] = [
            "derive-conclusion-exit-1" if calls == 1 else "derive-conclusion"
        ]
        if calls > 1:
            assert "unknown practice targets" in str(messages)
        return ModelResponse(parts=[TextPart(json.dumps(payload))])

    reviewer = NativePracticeDesignReviewClient(model=FunctionModel(respond))
    result = await reviewer.complete_review(
        settings=_settings(),
        source=_source(),
        proposal=proposal(),
        allowed_source_paths=("lecture-01.md",),
        messages=[
            {"role": "system", "content": "Review."},
            {"role": "user", "content": "Review this design."},
        ],
        catalogue={"e0": {"source_path": "lecture-01.md", "excerpt": "evidence"}},
    )
    assert calls == 2
    assert result["checks"][0]["target_ids"] == ["derive-conclusion"]

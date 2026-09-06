import json

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.course_practice_design_review_client import NativePracticeDesignReviewClient
from test_practice_design_semantic_review import _review_payload, _settings


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

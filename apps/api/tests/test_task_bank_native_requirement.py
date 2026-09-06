import json

import pytest
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.course_practice_design_planner import PracticeDesignPlanner
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.practice_evidence_catalogue import compact_evidence_anchors
from practice_design_test_helpers import proposal
from test_practice_design_semantic_review import _Registry, _source


@pytest.mark.asyncio
async def test_new_native_proposal_cannot_omit_both_fresh_task_categories():
    calls = []

    def respond(messages, info):
        payload = compact_evidence_anchors(proposal().model_dump(mode="json"), {})
        payload["targets"][0].pop("source_refs")
        return ModelResponse(parts=[TextPart(json.dumps(payload))])

    class Critic:
        async def complete_review(self, **kwargs):
            calls.append(kwargs)
            raise AssertionError("Incomplete bank must fail before semantic review.")

    planner = PracticeDesignPlanner(
        provider_registry=_Registry(),
        model=FunctionModel(respond),
        review_client=Critic(),
    )
    with pytest.raises(ModelExecutionError, match="valid design"):
        await planner.propose(
            source=_source(), source_revision="a" * 64, allowed_source_paths=("lecture-01.md",)
        )
    assert calls == []

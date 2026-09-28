import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.teaching_design_job import TeachingDesignJob, run_teaching_design_job
from practice_design_test_helpers import passing_review
from test_teaching_design_workspace import workspace as teaching_workspace  # noqa: F401


@pytest.mark.asyncio
async def test_completion_is_unavailable_until_the_current_saved_draft_passes_review(
    teaching_workspace,
):
    workspace = teaching_workspace
    calls = 0
    before = workspace.proposal()

    async def review(proposal):
        return passing_review()

    def model(messages, info):
        nonlocal calls
        calls += 1
        if calls <= 4:
            assert not info.output_tools, "Unreviewed teaching must remain in the tool loop"
            return ModelResponse(parts=[ToolCallPart("read", {"target_id": before.targets[0].id})])
        if calls == 5:
            assert not info.output_tools
            return ModelResponse(parts=[ToolCallPart("validate", {})])
        assert info.output_tools
        return ModelResponse(parts=[ToolCallPart("final_result", {"ready": True})])

    job = TeachingDesignJob(
        root=workspace.root / "agent",
        source=workspace.source,
        intent=workspace.intent,
        initial=before,
        paths=workspace.paths,
        source_revision="a" * 64,
        settings=ProviderSettings(
            provider="openai",
            model="openai/test",
            api_key_env="OPENAI_API_KEY",
            capabilities={ProviderCapability.CHAT, ProviderCapability.TOOL_CALLS},
        ),
        review=review,
        authorize=lambda: None,
    )
    result, _ = await run_teaching_design_job(job, model=FunctionModel(model))
    workspace.intent.require_matches(result)
    assert result == before
    assert calls == 6

import pytest
from pydantic_ai.messages import ModelResponse, ThinkingPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.teaching_design_job import TeachingDesignJob, run_teaching_design_job
from practice_design_test_helpers import passing_review
import test_teaching_design_workspace as workspace_fixtures


@pytest.mark.asyncio
async def test_thinking_only_exhaustion_resumes_saved_workspace_with_required_actions(tmp_path):
    workspace = workspace_fixtures.workspace.__wrapped__(tmp_path)
    initial = workspace.proposal()
    calls = 0

    async def review(proposal):
        return passing_review()

    def model(messages, info):
        nonlocal calls
        calls += 1
        assert info.model_settings.get("tool_choice") == ("required" if calls <= 6 else "auto")
        if calls <= 4:
            return ModelResponse(parts=[ThinkingPart("No actionable result")])
        if calls == 5:
            return ModelResponse(parts=[ToolCallPart("read", {"target_id": initial.targets[0].id})])
        if calls == 6:
            return ModelResponse(parts=[ToolCallPart("validate", {})])
        return ModelResponse(parts=[ToolCallPart("final_result", {"ready": True})])

    job = TeachingDesignJob(
        root=workspace.root / "agent",
        source=workspace.source,
        intent=workspace.intent,
        initial=initial,
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
    assert result == initial
    assert calls == 7


@pytest.mark.parametrize("reason", ["length", "content_filter"])
def test_policy_or_token_limit_failure_is_not_resumed(reason):
    from pydantic_ai.exceptions import UnexpectedModelBehavior
    from lecturepilot.teaching_response_recovery import no_action_response_exhausted

    assert not no_action_response_exhausted(
        UnexpectedModelBehavior("Exceeded maximum output retries (3)"),
        [ModelResponse(parts=[ThinkingPart("No action")], finish_reason=reason)],
    )


def test_invalid_tool_output_is_not_resumed_as_a_no_action_response():
    from pydantic_ai.exceptions import UnexpectedModelBehavior
    from lecturepilot.teaching_response_recovery import no_action_response_exhausted

    assert not no_action_response_exhausted(
        UnexpectedModelBehavior("Exceeded maximum output retries (3)"),
        [ModelResponse(parts=[ToolCallPart("final_result", {"ready": "invalid"})])],
    )

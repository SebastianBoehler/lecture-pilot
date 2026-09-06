import json
import sys
from types import SimpleNamespace

import pytest

from lecturepilot.course_canvas_planner import LiteLLMCoursePlanClient
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry


def install_provider(monkeypatch, completion):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=completion))
    return ProviderRegistry.from_env("openai/gpt-5.6-luna").require_ready([])


def response():
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content=json.dumps({"title": "Recovered", "sections": []})),
            )
        ]
    )


async def test_planner_recovers_transient_provider_failure_without_manual_retry(monkeypatch):
    calls = []

    async def completion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise TimeoutError("temporary outage")
        return response()

    async def no_wait(_seconds):
        pass

    settings = install_provider(monkeypatch, completion)
    monkeypatch.setattr("lecturepilot.model_usage.asyncio.sleep", no_wait)
    result = await LiteLLMCoursePlanClient().complete_plan(settings=settings, messages=[])
    assert result["title"] == "Recovered"
    assert len(calls) == 2


async def test_planner_uses_low_reasoning_without_test_only_output_cap(monkeypatch):
    async def completion(**kwargs):
        assert kwargs["reasoning_effort"] == "low"
        assert "max_tokens" not in kwargs
        return response()

    settings = install_provider(monkeypatch, completion)
    await LiteLLMCoursePlanClient().complete_plan(settings=settings, messages=[])


async def test_planner_preserves_actionable_configuration_error_without_retry(monkeypatch):
    calls = 0

    async def completion(**_kwargs):
        nonlocal calls
        calls += 1
        raise ProviderConfigurationError("Account spending is paused.")

    settings = install_provider(monkeypatch, completion)
    with pytest.raises(ProviderConfigurationError, match="Account spending is paused"):
        await LiteLLMCoursePlanClient().complete_plan(settings=settings, messages=[])
    assert calls == 1


async def test_section_does_not_reprompt_for_permanent_configuration_error():
    from lecturepilot.course_canvas_section_planner import plan_sections_individually
    from practice_design_test_helpers import practice_design_for_canvas
    from test_course_canvas_section_concurrency import _settings, _source_document

    class UnconfiguredModel:
        calls = 0

        async def complete_plan(self, **kwargs):
            self.calls += 1
            raise ProviderConfigurationError("Missing provider credentials")

    source = _source_document(1)
    client = UnconfiguredModel()
    with pytest.raises(ProviderConfigurationError, match="Missing provider"):
        await plan_sections_individually(
            model_client=client,
            settings=_settings(),
            source_document=source,
            practice_design=practice_design_for_canvas(source),
        )
    assert client.calls == 1

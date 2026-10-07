import pytest
from lecturepilot import practice_exam_planner
from lecturepilot.practice_exam_planner import NativePracticeExamClient
from practice_exam_planner_fixtures import _Registry
from lecturepilot.models import ProviderCapability


@pytest.mark.asyncio
async def test_exam_client_uses_metered_native_schema_and_high_reasoning(monkeypatch):
    calls = []

    async def complete(**kwargs):
        calls.append(kwargs)
        return {"title": "Exam"}

    monkeypatch.setattr(practice_exam_planner, "native_completion", complete)
    recorder = object()
    settings = _Registry().require_ready(
        [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
    )
    schema = {"json_schema": {"schema": {"type": "object"}}}
    result = await NativePracticeExamClient(recorder).complete_exam(
        settings=settings,
        messages=[{"role": "system", "content": "Author exam"}],
        response_format=schema,
        max_tokens=12000,
    )
    assert result == {"title": "Exam"}
    assert calls[0]["recorder"] is recorder
    assert calls[0]["response_format"] is schema
    assert calls[0]["reasoning_effort"] == "high"
    assert calls[0]["stage"] == "practice_exam"
    assert calls[0]["max_tokens"] == 12000


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "schema_name,expected_tier",
    [
        ("lecturepilot_practice_exam", None),
        ("lecturepilot_practice_exam_review", "critic"),
    ],
)
async def test_exam_review_routes_to_critic_tier_and_authoring_keeps_primary(
    monkeypatch, schema_name, expected_tier
):
    calls = []

    async def complete(**kwargs):
        calls.append(kwargs)
        return {"reviews": []}

    monkeypatch.setattr(practice_exam_planner, "native_completion", complete)
    settings = _Registry().require_ready(
        [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
    )
    await NativePracticeExamClient().complete_exam(
        settings=settings,
        messages=[{"role": "system", "content": "Review"}],
        response_format={"json_schema": {"name": schema_name, "schema": {"type": "object"}}},
        max_tokens=4000,
    )
    assert calls[0].get("tier") == expected_tier
    assert calls[0]["settings"] is settings

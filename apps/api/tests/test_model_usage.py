from __future__ import annotations

from types import SimpleNamespace

import pytest

from lecturepilot.model_usage import complete_with_usage, usage_tokens_from_response


def test_extracts_actual_and_detailed_tokens_from_provider_response() -> None:
    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=120,
            completion_tokens=35,
            total_tokens=155,
            prompt_tokens_details=SimpleNamespace(cached_tokens=24),
            completion_tokens_details=SimpleNamespace(reasoning_tokens=11),
        )
    )

    assert usage_tokens_from_response(response) == {
        "input_tokens": 120,
        "output_tokens": 35,
        "total_tokens": 155,
        "cached_input_tokens": 24,
        "reasoning_tokens": 11,
    }


def test_missing_provider_usage_is_recorded_as_zero_not_estimated() -> None:
    assert usage_tokens_from_response(SimpleNamespace()) == {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cached_input_tokens": 0,
        "reasoning_tokens": 0,
    }


@pytest.mark.asyncio
async def test_model_request_emits_stage_latency_queue_and_token_metadata(monkeypatch) -> None:
    events: list[tuple[str, dict]] = []

    async def completion(**_kwargs):
        return SimpleNamespace(
            usage=SimpleNamespace(
                prompt_tokens=120,
                completion_tokens=35,
                total_tokens=155,
            )
        )

    monkeypatch.setattr(
        "lecturepilot.model_usage.emit_metadata_event",
        lambda event, **values: events.append((event, values)),
    )

    await complete_with_usage(
        None,
        completion,
        model="openai/test-model",
        usage_stage="canvas_section",
    )

    assert events[0][0] == "model.request_finished"
    values = events[0][1]
    assert values["error"] is False
    assert values["stage"] == "canvas_section"
    assert values["status"] == "succeeded"
    assert values["provider"] == "openai"
    assert values["input_tokens"] == 120
    assert values["output_tokens"] == 35
    assert values["total_tokens"] == 155
    assert values["queue_wait_ms"] >= 0
    assert values["latency_ms"] >= 0

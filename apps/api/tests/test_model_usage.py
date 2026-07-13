from __future__ import annotations

from types import SimpleNamespace

from lecturepilot.model_usage import usage_tokens_from_response


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

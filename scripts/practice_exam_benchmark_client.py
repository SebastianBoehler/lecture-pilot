"""Meter real planner calls without storing benchmark usage in learner databases."""

from __future__ import annotations

import json
from math import isfinite
from time import perf_counter

from lecturepilot.model_usage import usage_tokens_from_response
from lecturepilot.native_completion import native_completion


class BenchmarkBudgetExceeded(ValueError):
    pass


def verified_model_prices(prices, model):
    price = prices.get(model) if isinstance(prices, dict) else None
    if not isinstance(price, dict) or any(
        type(price.get(key)) not in {int, float}
        or not isfinite(price[key])
        or price[key] < 0
        for key in ("input", "cached_input", "output")
    ):
        raise BenchmarkBudgetExceeded(
            f"Missing verified finite token prices for {model}."
        )
    return price


class BenchmarkMeter:
    def __init__(self, prices: dict, budget_usd: float):
        if not isfinite(budget_usd) or budget_usd <= 0:
            raise BenchmarkBudgetExceeded("USD budget must be positive and finite.")
        self.prices = prices
        self.budget_usd = budget_usd
        self.spent_usd = 0.0
        self.unknown_cost_reserve = 0.0
        self.calls: list[dict] = []

    def reserve(
        self, model: str, messages: list[dict], response_format: dict, max_tokens: int
    ):
        # UTF-8 bytes upper-bound text tokens; include the native schema and request overhead.
        input_bound = (
            len(json.dumps([messages, response_format], ensure_ascii=False).encode())
            + 4096
        )
        price = verified_model_prices(self.prices, model)
        bound = (
            6
            * (
                (input_bound + 2 * max_tokens) * price["input"]
                + max_tokens * price["output"]
            )
            / 1_000_000
        )
        if self.spent_usd + self.unknown_cost_reserve + bound > self.budget_usd:
            raise BenchmarkBudgetExceeded(
                "Next request, schema repairs and retries would exceed the USD budget."
            )
        return bound

    def record_response(self, response, *, model, request_id=None, attempt=1):
        tokens = usage_tokens_from_response(response)
        price = verified_model_prices(self.prices, model)
        cached = min(tokens["cached_input_tokens"], tokens["input_tokens"])
        cost = (
            (tokens["input_tokens"] - cached) * price["input"]
            + cached * price["cached_input"]
            + tokens["output_tokens"] * price["output"]
        ) / 1_000_000
        self.spent_usd += cost
        self.calls.append(
            {
                "model": model,
                "attempt": attempt,
                "status": "succeeded",
                **tokens,
                "estimated_usd": cost,
            }
        )

    def record_failure(self, *, model, request_id, attempt, error_type):
        self.calls.append(
            {
                "model": model,
                "attempt": attempt,
                "status": "failed",
                "error_type": error_type,
            }
        )


class BenchmarkExamClient:
    def __init__(self, meter: BenchmarkMeter):
        self.meter = meter
        self.outputs: list[dict] = []

    async def complete_exam(self, *, settings, messages, response_format, max_tokens):
        reserved = self.meter.reserve(
            settings.model, messages, response_format, max_tokens
        )
        start = perf_counter()
        call_start = len(self.meter.calls)
        try:
            # Controlled comparisons always use the requested model, including critics.
            payload = await native_completion(
                settings=settings,
                messages=messages,
                response_format=response_format,
                max_tokens=max_tokens,
                stage="practice_exam_benchmark",
                recorder=self.meter,
                temperature=0.2,
                reasoning_effort="high",
            )
            self.outputs.append(
                {"schema": response_format["json_schema"]["name"], "payload": payload}
            )
            return payload
        finally:
            calls = self.meter.calls[call_start:]
            for call in calls:
                call["request_elapsed_seconds"] = round(perf_counter() - start, 3)
                call["schema"] = response_format["json_schema"]["name"]
            if any(call["status"] == "failed" for call in calls):
                # Failed/timeout requests may still be billed; never silently treat them as free.
                self.meter.unknown_cost_reserve += reserved

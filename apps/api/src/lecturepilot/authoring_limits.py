"""Bound a complete authoring session, including nested semantic reviews."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from lecturepilot.model_client import ModelExecutionError

AUTHORING_REQUEST_LIMIT = 60
AUTHORING_INPUT_TOKEN_LIMIT = 1_000_000
AUTHORING_OUTPUT_TOKEN_LIMIT = 120_000
AUTHORING_DEADLINE_SECONDS = 15 * 60


class AuthoringBudgetExceeded(ModelExecutionError):
    """Saved drafts remain resumable after an explicit authoring budget failure."""


@dataclass
class AuthoringBudget:
    request_limit: int
    input_tokens_limit: int
    output_tokens_limit: int
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def reserve_request(self):
        self.check_tokens()
        if self.requests >= self.request_limit:
            raise AuthoringBudgetExceeded("Model job request budget exhausted.")
        self.requests += 1

    def record_tokens(self, usage):
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.check_tokens()

    def check_tokens(self):
        if (
            self.input_tokens >= self.input_tokens_limit
            or self.output_tokens >= self.output_tokens_limit
        ):
            raise AuthoringBudgetExceeded("Model job token budget exhausted.")


_current_budget: ContextVar[AuthoringBudget | None] = ContextVar("authoring_budget", default=None)


def current_authoring_budget():
    return _current_budget.get()


@contextmanager
def authoring_budget(
    *,
    request_limit=AUTHORING_REQUEST_LIMIT,
    input_tokens_limit=AUTHORING_INPUT_TOKEN_LIMIT,
    output_tokens_limit=AUTHORING_OUTPUT_TOKEN_LIMIT,
):
    # Nested jobs and concurrent critics consume the same request-local budget.
    if _current_budget.get() is not None:
        yield _current_budget.get()
        return
    budget = AuthoringBudget(request_limit, input_tokens_limit, output_tokens_limit)
    token = _current_budget.set(budget)
    try:
        yield budget
    finally:
        _current_budget.reset(token)

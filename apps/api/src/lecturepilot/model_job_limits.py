"""Bound complete planning workflows, including their repairs and reviewers."""

import asyncio
from functools import wraps

from lecturepilot.authoring_limits import (
    authoring_budget,
    AuthoringBudgetExceeded,
    AUTHORING_DEADLINE_SECONDS,
)


def bounded_model_job(function):
    @wraps(function)
    async def run(*args, **kwargs):
        with authoring_budget():
            try:
                async with asyncio.timeout(AUTHORING_DEADLINE_SECONDS):
                    return await function(*args, **kwargs)
            except TimeoutError as exc:
                raise AuthoringBudgetExceeded("Model planning job deadline reached.") from exc

    return run

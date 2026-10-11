"""Bounded continuation of saved implementation work under unchanged ownership."""

import asyncio
import hashlib
import json

from lecturepilot.authoring_limits import (
    AUTHORING_DEADLINE_SECONDS,
    AuthoringBudgetExceeded,
    authoring_budget,
)
from lecturepilot.metadata_events import emit_metadata_event
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_provider_errors import is_retryable_provider_error


IMPLEMENTATION_ATTEMPTS = 3


def _targets_digest(root):
    digest = hashlib.sha256()
    for path in sorted(root.glob("*/draft.json")):
        saved = json.loads(path.read_text())
        digest.update(str(path.relative_to(root)).encode())
        digest.update(json.dumps(saved.get("targets", {}), sort_keys=True).encode())
    return digest.hexdigest()


async def continue_saved_implementation(run, **kwargs):
    root, authorize = kwargs["root"], kwargs["authorize"]
    for attempt in range(IMPLEMENTATION_ATTEMPTS):
        authorize()
        before = _targets_digest(root)
        try:
            with authoring_budget():
                try:
                    async with asyncio.timeout(AUTHORING_DEADLINE_SECONDS):
                        return await run(**kwargs)
                except TimeoutError as exc:
                    raise AuthoringBudgetExceeded(
                        "Teaching implementation deadline reached; saved targets can resume."
                    ) from exc
        except ModelExecutionError as exc:
            progressed = before != _targets_digest(root)
            resumable = (
                progressed
                if isinstance(exc, AuthoringBudgetExceeded)
                else is_retryable_provider_error(exc)
            )
            if not resumable or attempt + 1 == IMPLEMENTATION_ATTEMPTS:
                raise
            authorize()
            emit_metadata_event(
                "teaching_implementation.continued",
                attempt=attempt + 2,
                reason="budget_with_progress"
                if isinstance(exc, AuthoringBudgetExceeded)
                else "temporary_provider_error",
            )

"""Server enforcement for pending independent and delayed checks."""

from fastapi import HTTPException

INDEPENDENT_ATTEMPT_STAGES = frozenset({"independent_exit", "delayed_transfer"})


def reject_chat_during_independent_attempt(
    *, checkpoint_gate_id: str | None, stage: str | None
) -> None:
    if checkpoint_gate_id is None and stage in INDEPENDENT_ATTEMPT_STAGES:
        raise HTTPException(status_code=409, detail="independent_attempt_in_progress")

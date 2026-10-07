"""Correct support-exhaustion flags written by the original remediation."""

from lecturepilot.coaching_task_bank import canonical_task_id


def normalize_pending_support(progress, gates):
    pending = progress.pending_check
    if pending is None or not pending.support_exhausted:
        return
    gate = next(
        (
            gate
            for gate in gates
            if gate.id == pending.gate_id and gate.revision == pending.gate_revision
        ),
        None,
    )
    if gate is None:
        return
    last = next(
        (
            turn
            for turn in reversed(progress.turns)
            if turn.gate_id == gate.id and turn.gate_revision == gate.revision
        ),
        None,
    )
    if gate.hint_ladder and not (last and last.gate_status == "passed"):
        return
    updates = {"support_exhausted": False}
    if not gate.hint_ladder and gate.practice_target_id is None and pending.stage == "exit_support":
        updates.update(stage="independent_exit", bank_exhausted=False)
        key = f"{gate.id}@{gate.revision}@{pending.task_id or canonical_task_id(pending.stage)}"
        exposure = progress.task_exposures.get(key)
        if exposure is not None:
            # The old automatic transition marked this task supported even though
            # ordinary checkpoints have no approved support to expose.
            progress.task_exposures[key] = exposure.model_copy(update={"supported": False})
    progress.pending_check = pending.model_copy(update=updates)

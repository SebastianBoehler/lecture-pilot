"""Task identities and persisted exposure, scoped to the exact published gate."""

from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class TaskExposure(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    gate_id: str
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    task_id: str = Field(min_length=1, max_length=80)
    exposed_at: AwareDatetime
    supported: bool = False
    answered: bool = False


def canonical_task_id(stage: str) -> str:
    if stage.startswith("diagnostic"):
        return "baseline"
    if stage.startswith("delayed"):
        return "delayed-transfer"
    return "independent-exit"


def task_prompt(gate, task_id: str) -> str:
    canonical = {
        "baseline": gate.prompt,
        "independent-exit": gate.independent_exit_task or gate.prompt,
        "delayed-transfer": gate.transfer_prompt,
    }
    if task_id in canonical:
        return canonical[task_id]
    return next(task.prompt for task in gate.supplemental_tasks if task.id == task_id)


def task_ids_for_stage(gate, stage: str) -> list[str]:
    return [
        canonical_task_id(stage),
        *(task.id for task in gate.supplemental_tasks if task.stage == stage),
    ]


def exposed_ids(progress, gate_id: str, revision: str) -> list[str]:
    ids = [
        item.task_id
        for item in progress.task_exposures.values()
        if item.gate_id == gate_id and item.gate_revision == revision
    ]
    # Older snapshots did not record task identities; their stages still prove exposure.
    ids.extend(
        canonical_task_id(turn.attempt_kind.replace("supported_retry", "exit_support"))
        for turn in progress.turns
        if turn.gate_id == gate_id and turn.gate_revision == revision and not turn.task_id
    )
    pending = progress.pending_check
    if pending and pending.gate_id == gate_id and pending.gate_revision == revision:
        ids.append(pending.task_id or canonical_task_id(pending.stage))
    return sorted(set(ids))


def record_task_exposure(progress, pending, now: datetime, *, answered: bool = False):
    task_id = pending.task_id or canonical_task_id(pending.stage)
    key = f"{pending.gate_id}@{pending.gate_revision}@{task_id}"
    old = progress.task_exposures.get(key)
    progress.task_exposures[key] = TaskExposure(
        gate_id=pending.gate_id,
        gate_revision=pending.gate_revision,
        task_id=task_id,
        exposed_at=old.exposed_at if old else now,
        supported=bool((old and old.supported) or pending.stage.endswith("support")),
        answered=answered or bool(old and old.answered),
    )

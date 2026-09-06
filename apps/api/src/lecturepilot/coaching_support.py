"""Explicit help is persisted before approved content can leave the backend."""

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.coaching_task_bank import (
    canonical_task_id,
    record_task_exposure,
    exposed_ids,
    task_ids_for_stage,
)
from lecturepilot.coaching_state_models import HintExposure, hint_exposure_key
from lecturepilot.durable_files import exclusive_file_lock


class CoachingSupportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    gate_id: str = Field(min_length=1, max_length=160)
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    task_id: str = Field(min_length=1, max_length=80)
    issued_at: str = Field(min_length=1, max_length=80)


def request_support(
    store, *, user_id, course_id, lecture_id, gate, request, now: datetime | None = None
):
    ids = dict(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
    with exclusive_file_lock(store._path(**ids)):
        progress = store.read(**ids)
        pending = progress.pending_check
        if pending is None or (
            request.gate_id != gate.id
            or request.gate_revision != gate.revision
            or pending.gate_id != gate.id
            or pending.gate_revision != gate.revision
            or request.task_id != (pending.task_id or canonical_task_id(pending.stage))
            or request.issued_at != pending.issued_at.isoformat()
        ):
            raise ValueError("The pending task changed; reload before requesting help.")
        if pending.stage.endswith("support"):
            raise ValueError("Help is already recorded for this task.")
        hint = next(iter(gate.hint_ladder), None)
        if hint is None:
            raise ValueError("This reviewed task has no approved help available.")
        stage = {
            "diagnostic": "diagnostic_support",
            "independent_exit": "exit_support",
            "delayed_transfer": "delayed_support",
        }[pending.stage]
        instant = max(now or datetime.now(UTC), pending.issued_at + timedelta(microseconds=1))
        exposed = exposed_ids(progress, gate.id, gate.revision)
        exhausted = pending.stage != "diagnostic" and not any(
            task_id not in exposed for task_id in task_ids_for_stage(gate, pending.stage)
        )
        pending = pending.model_copy(
            update={
                "stage": stage,
                "kind": "standard",
                "task_id": request.task_id,
                "assistance_level": hint.level,
                "assistance_content": hint.content,
                "issued_at": instant,
                "bank_exhausted": exhausted,
            }
        )
        progress.pending_check = pending
        progress.hint_exposures[hint_exposure_key(gate.revision, hint.level)] = HintExposure(
            gate_id=gate.id,
            gate_revision=gate.revision,
            assistance_level=hint.level,
            content=hint.content,
            exposed_at=instant,
        )
        record_task_exposure(progress, pending, instant)
        progress.updated_at = instant
        store._write(**ids, progress=progress)
        return progress

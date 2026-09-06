"""Categorical evidence survives bounded conversational history retention."""

from pydantic import BaseModel, ConfigDict, Field


class GoalEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    gate_id: str
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    supported: bool = False
    independent: bool = False
    delayed: bool = False
    missing_evidence_ids: list[str] = Field(default_factory=list, max_length=40)


def accumulate_goal_evidence(evidence, turn):
    key = f"{turn.gate_id}@{turn.gate_revision}"
    item = evidence.setdefault(
        key,
        GoalEvidence(
            gate_id=turn.gate_id,
            gate_revision=turn.gate_revision,
        ),
    )
    item.missing_evidence_ids = list(turn.missing_evidence_ids)
    if turn.gate_status == "passed":
        if turn.attempt_kind == "supported_retry":
            item.supported = True
        elif turn.attempt_kind in {"independent", "independent_exit"}:
            item.independent = True
        elif turn.attempt_kind == "delayed_transfer":
            item.delayed = True

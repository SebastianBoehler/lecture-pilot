from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from pydantic import BaseModel


class AnalyticsGateMetric(BaseModel):
    gate_id: str
    total_events: int
    unique_learners: int
    latest_activity: str | None
    status_counts: dict[str, int]
    attendance_split: dict[str, int]
    independent_attempts: int
    independent_passes: int
    supported_attempts: int
    transfer_attempts: int
    independent_transfer_passes: int
    assistance_level_counts: dict[str, int]
    evidence_counts: dict[str, int]


@dataclass
class _GateState:
    total_events: int = 0
    learners: set[str] = field(default_factory=set)
    latest_activity: str = ""
    status: Counter[str] = field(default_factory=Counter)
    attendance: Counter[str] = field(default_factory=Counter)
    assistance: Counter[str] = field(default_factory=Counter)
    evidence: Counter[str] = field(default_factory=Counter)
    independent_attempts: int = 0
    independent_passes: int = 0
    supported_attempts: int = 0
    transfer_attempts: int = 0
    independent_transfer_passes: int = 0


class GateMetricsAccumulator:
    def __init__(self) -> None:
        self._groups: dict[str, _GateState] = {}

    def record(self, event: dict) -> None:
        if event.get("type") != "gate_decision":
            return
        state = self._groups.setdefault(str(event.get("gate_id") or "gate"), _GateState())
        state.total_events += 1
        if event.get("user_key"):
            state.learners.add(str(event["user_key"]))
        state.latest_activity = max(state.latest_activity, str(event.get("created_at") or ""))
        status = str(event.get("status") or "unknown")
        state.status[status] += 1
        state.attendance[str(event.get("attendance") or "unknown")] += 1
        state.assistance[str(event.get("assistance_level") or "unknown")] += 1
        state.evidence.update(_evidence_ids(event))
        independent = event.get("independent_attempt") is True
        transfer = event.get("transfer_attempt") is True
        state.independent_attempts += independent
        state.independent_passes += independent and status == "passed"
        state.supported_attempts += (
            status != "not_assessed" and event.get("support_before_attempt") is True
        )
        state.transfer_attempts += transfer
        state.independent_transfer_passes += transfer and independent and status == "passed"

    def metrics(self) -> list[AnalyticsGateMetric]:
        return [self._metric(gate_id, self._groups[gate_id]) for gate_id in sorted(self._groups)]

    @staticmethod
    def _metric(gate_id: str, state: _GateState) -> AnalyticsGateMetric:
        return AnalyticsGateMetric(
            gate_id=gate_id,
            total_events=state.total_events,
            unique_learners=len(state.learners),
            latest_activity=state.latest_activity or None,
            status_counts=dict(sorted(state.status.items())),
            attendance_split=dict(sorted(state.attendance.items())),
            independent_attempts=state.independent_attempts,
            independent_passes=state.independent_passes,
            supported_attempts=state.supported_attempts,
            transfer_attempts=state.transfer_attempts,
            independent_transfer_passes=state.independent_transfer_passes,
            assistance_level_counts=dict(sorted(state.assistance.items())),
            evidence_counts=dict(sorted(state.evidence.items())),
        )


def gate_metrics(events: Iterable[dict]) -> list[AnalyticsGateMetric]:
    accumulator = GateMetricsAccumulator()
    for event in events:
        accumulator.record(event)
    return accumulator.metrics()


def _evidence_ids(event: dict) -> list[str]:
    value = event.get("evidence_ids")
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []

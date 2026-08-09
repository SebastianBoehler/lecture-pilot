from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from pydantic import BaseModel

from lecturepilot.analytics_outcomes import (
    AnalyticsOutcomeCell,
    AnalyticsVersionStatus,
    outcome_cell,
    version_sort_key,
    version_status,
)

_OUTCOME_KINDS = ("independent", "supported_retry", "delayed_transfer")


class AnalyticsGateMetric(BaseModel):
    gate_id: str
    gate_revision: str
    publication_version: int
    version_status: AnalyticsVersionStatus
    activity_events: int
    unique_learners: int
    independent_first_pass: AnalyticsOutcomeCell
    supported_retry: AnalyticsOutcomeCell
    delayed_transfer: AnalyticsOutcomeCell


@dataclass
class _LearnerAttempt:
    attempt_index: int
    passed: bool


@dataclass
class _GateState:
    gate_revision: str
    publication_version: int
    activity_events: int = 0
    learners: set[str] = field(default_factory=set)
    outcomes: dict[str, dict[str, _LearnerAttempt]] = field(
        default_factory=lambda: {kind: {} for kind in _OUTCOME_KINDS}
    )


class GateMetricsAccumulator:
    def __init__(
        self,
        *,
        current_publication_version: int,
        current_gate_revisions: dict[str, str],
    ) -> None:
        self.current_publication_version = current_publication_version
        self.current_gate_revisions = current_gate_revisions
        self._groups: dict[tuple[str, str, int], _GateState] = {}

    def record(self, event: dict) -> None:
        if event.get("type") != "gate_decision":
            return
        gate_id = str(event["gate_id"])
        gate_revision = str(event["gate_revision"])
        publication_version = _publication_version(event)
        key = gate_id, gate_revision, publication_version
        state = self._groups.setdefault(
            key,
            _GateState(
                gate_revision=gate_revision,
                publication_version=publication_version,
            ),
        )
        state.activity_events += 1
        learner_key = str(event["user_key"])
        state.learners.add(learner_key)
        kind = str(event["attempt_kind"])
        if kind not in _OUTCOME_KINDS:
            return
        attempt_index = event["attempt_index"]
        if not isinstance(attempt_index, int) or attempt_index < 1:
            return
        if kind == "independent" and attempt_index != 1:
            return
        attempt = _LearnerAttempt(
            attempt_index=attempt_index,
            passed=event["status"] == "passed",
        )
        current = state.outcomes[kind].get(learner_key)
        if current is None or attempt_index < current.attempt_index:
            state.outcomes[kind][learner_key] = attempt

    def metrics(self) -> list[AnalyticsGateMetric]:
        metrics = [self._metric(key[0], state) for key, state in self._groups.items()]
        return sorted(
            metrics,
            key=lambda item: (
                item.gate_id,
                version_sort_key(item.publication_version, item.version_status),
            ),
        )

    def _metric(self, gate_id: str, state: _GateState) -> AnalyticsGateMetric:
        status = version_status(
            state.publication_version,
            self.current_publication_version,
        )
        if status == "current" and (
            self.current_gate_revisions.get(gate_id) != state.gate_revision
        ):
            status = "historical"
        return AnalyticsGateMetric(
            gate_id=gate_id,
            gate_revision=state.gate_revision,
            publication_version=state.publication_version,
            version_status=status,
            activity_events=state.activity_events,
            unique_learners=len(state.learners),
            independent_first_pass=_cell("independent_first_pass", state.outcomes["independent"]),
            supported_retry=_cell("supported_retry", state.outcomes["supported_retry"]),
            delayed_transfer=_cell("delayed_transfer", state.outcomes["delayed_transfer"]),
        )


def gate_metrics(
    events: Iterable[dict],
    *,
    current_publication_version: int,
    current_gate_revisions: dict[str, str],
) -> list[AnalyticsGateMetric]:
    accumulator = GateMetricsAccumulator(
        current_publication_version=current_publication_version,
        current_gate_revisions=current_gate_revisions,
    )
    for event in events:
        accumulator.record(event)
    return accumulator.metrics()


def _cell(evidence_type: str, attempts: dict[str, _LearnerAttempt]) -> AnalyticsOutcomeCell:
    return outcome_cell(
        evidence_type,
        {learner_key: attempt.passed for learner_key, attempt in attempts.items()},
    )


def _publication_version(event: dict) -> int:
    return int(event["publication_version"])

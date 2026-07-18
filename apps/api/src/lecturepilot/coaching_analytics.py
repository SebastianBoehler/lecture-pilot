from __future__ import annotations

from collections import Counter, defaultdict

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


def gate_metrics(events: list[dict]) -> list[AnalyticsGateMetric]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        if event.get("type") == "gate_decision":
            grouped[str(event.get("gate_id") or "gate")].append(event)
    return [_gate_metric(gate_id, items) for gate_id, items in sorted(grouped.items())]


def _gate_metric(gate_id: str, events: list[dict]) -> AnalyticsGateMetric:
    latest = max(events, key=lambda item: str(item.get("created_at") or ""))
    independent = [event for event in events if event.get("independent_attempt") is True]
    transfers = [event for event in events if event.get("transfer_attempt") is True]
    assessed = [event for event in events if event.get("status") != "not_assessed"]
    return AnalyticsGateMetric(
        gate_id=gate_id,
        total_events=len(events),
        unique_learners=len(
            {str(event.get("user_key")) for event in events if event.get("user_key")}
        ),
        latest_activity=str(latest.get("created_at") or "") or None,
        status_counts=_counts(events, "status"),
        attendance_split=_counts(events, "attendance"),
        independent_attempts=len(independent),
        independent_passes=sum(event.get("status") == "passed" for event in independent),
        supported_attempts=sum(event.get("support_before_attempt") is True for event in assessed),
        transfer_attempts=len(transfers),
        independent_transfer_passes=sum(
            event.get("status") == "passed" and event.get("independent_attempt") is True
            for event in transfers
        ),
        assistance_level_counts=_counts(events, "assistance_level"),
        evidence_counts=dict(
            sorted(
                Counter(
                    evidence_id for event in events for evidence_id in _evidence_ids(event)
                ).items()
            )
        ),
    )


def _counts(events: list[dict], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(event.get(key) or "unknown") for event in events).items()))


def _evidence_ids(event: dict) -> list[str]:
    value = event.get("evidence_ids")
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []

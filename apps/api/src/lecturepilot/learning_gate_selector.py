from __future__ import annotations

from collections.abc import Mapping

from lecturepilot.learning_map import LearningMap, LearningMapGate
from lecturepilot.quality_gate_models import QualityGateDecision, QualityGateStatus


def select_active_gate(
    learning_map: LearningMap,
    *,
    requested_gate_id: str | None = None,
    focused_section_id: str | None = None,
    latest_decisions: Mapping[str, QualityGateDecision] | None = None,
) -> LearningMapGate | None:
    """Select one open gate using only the published contract and learner decisions."""
    decisions = latest_decisions or {}
    gates = {gate.id: gate for gate in learning_map.gates}
    passed = {
        gate_id
        for gate_id, decision in decisions.items()
        if decision.status == QualityGateStatus.PASSED
    }

    if requested_gate_id in gates and requested_gate_id not in passed:
        return gates[requested_gate_id]

    if focused_section_id:
        focused = next(
            (
                gate
                for gate in learning_map.gates
                if gate.section_id == focused_section_id and gate.id not in passed
            ),
            None,
        )
        if focused is not None:
            return focused

    pending = next(
        (
            gate
            for gate in learning_map.gates
            if gate.id not in passed
            and (decision := decisions.get(gate.id)) is not None
            and decision.status == QualityGateStatus.NEEDS_EVIDENCE
        ),
        None,
    )
    if pending is not None:
        return pending
    return next((gate for gate in learning_map.gates if gate.id not in passed), None)

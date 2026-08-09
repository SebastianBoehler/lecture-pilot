import json
from pathlib import Path

from auth_helpers import professor_headers, student_headers
from lecturepilot.models import AgentTurnResult, QualityGateDecision, QualityGateStatus
from test_analytics_routes import _client


def test_only_bound_quality_gate_attempt_is_recorded_in_analytics(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.agent_harness = _GateHarness()
    payload = {
        "course_id": "demo-course",
        "lecture_id": "lecture-01",
        "attendance": "present",
        "message": "Please test my risk understanding.",
        "canvas_state": {"focused_section_id": "risk"},
    }

    first = client.post("/agent/turn", headers=student_headers("student-a"), json=payload)
    assert first.json()["quality_gate"]["status"] == "not_assessed"
    payload["message"] = "I combine posterior probabilities with each action's loss."
    second = client.post("/agent/turn", headers=student_headers("student-a"), json=payload)
    assert second.json()["quality_gate"]["status"] == "passed"

    summary = client.get(
        "/admin/courses/demo-course/lectures/lecture-01/analytics",
        headers=professor_headers(),
    )
    gate = summary.json()["gates"][0]
    assert gate["gate_id"] == "risk-evidence-check"
    assert gate["status_counts"] == {"passed": 1}
    assert gate["independent_attempts"] == 1
    assert gate["independent_passes"] == 1
    assert gate["supported_attempts"] == 0
    assert gate["assistance_level_counts"] == {"prompt": 1}
    assert gate["evidence_counts"] == {"risk-evidence-check": 1}
    events = client.app.state.analytics_store.events(
        course_id="demo-course", lecture_id="lecture-01"
    )
    assert "I combine posterior probabilities" not in json.dumps(events)


class _GateHarness:
    def __init__(self) -> None:
        self.calls = 0

    async def run_turn(self, *_args, **_kwargs):
        self.calls += 1
        first = self.calls == 1
        return AgentTurnResult(
            message="Answer the risk check." if first else "Gate passed.",
            model="test-harness",
            quality_gate=QualityGateDecision(
                gate_id="risk-gate",
                status=QualityGateStatus.NOT_ASSESSED if first else QualityGateStatus.PASSED,
                reason="Waiting for evidence." if first else "Complete evidence.",
                next_prompt=("Explain how posterior and loss select an action." if first else None),
                evidence_ids=[] if first else ["risk-evidence-check"],
            ),
        )

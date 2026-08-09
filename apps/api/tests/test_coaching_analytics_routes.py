from pathlib import Path

from auth_helpers import professor_headers
from test_analytics_routes import _client
from test_learning_outcome_analytics import _persist_gate, _prepare_gate


def test_only_bound_quality_gate_attempt_is_recorded_in_analytics(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _persist_gate(client, _prepare_gate(client, "student-a"), "independent", 1, True)

    summary = client.get(
        "/admin/courses/demo-course/lectures/lecture-01/analytics",
        headers=professor_headers(),
    )
    gate = summary.json()["gates"][0]
    assert gate["gate_id"] == "risk-evidence-check"
    assert gate["activity_events"] == 1
    assert gate["version_status"] == "current"
    assert gate["independent_first_pass"] == {
        "evidence_type": "independent_first_pass",
        "sample_size": 1,
        "data_status": "insufficient_data",
        "rate": None,
    }
    assert gate["supported_retry"]["sample_size"] == 0
    assert gate["delayed_transfer"]["sample_size"] == 0
    assert "status_counts" not in gate
    assert "assistance_level_counts" not in gate
    assert "evidence_counts" not in gate

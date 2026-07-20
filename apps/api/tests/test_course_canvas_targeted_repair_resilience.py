from pathlib import Path

from lecturepilot.model_client import ModelExecutionError
from test_course_canvas_targeted_repair import (
    _TargetedRepairPlanner,
    _client_contract_headers,
    _course_client,
)
from auth_helpers import professor_headers


def test_transient_repair_failure_keeps_the_surgical_candidate(tmp_path: Path) -> None:
    client = _course_client(tmp_path)
    planner = _TransientRepairPlanner()
    client.app.state.course_planner = planner
    path = "/admin/courses/targeted-repair/lectures/lecture-01/canvas/draft"

    failed = client.post(
        path,
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "targeted-resilience-failure-0001",
        },
    )
    transient = client.post(
        f"{path}/repair",
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "targeted-resilience-transient-0001",
        },
    )
    repaired = client.post(
        f"{path}/repair",
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "targeted-resilience-success-0001",
        },
    )

    assert failed.status_code == 503
    assert transient.status_code == 503
    assert transient.headers["X-Generation-Repairable"] == "true"
    assert repaired.status_code == 200
    assert planner.full_repair_called is False
    assert planner.repair_attempts == 2


class _TransientRepairPlanner(_TargetedRepairPlanner):
    def __init__(self) -> None:
        super().__init__()
        self.repair_attempts = 0

    async def repair_section(self, *args, **kwargs):
        self.repair_attempts += 1
        if self.repair_attempts == 1:
            raise ModelExecutionError("Course planner model request failed.")
        return await super().repair_section(*args, **kwargs)

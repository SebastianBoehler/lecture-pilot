from pathlib import Path

from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
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
    assert transient.status_code == 502
    assert "X-Generation-Repairable" not in transient.headers
    assert repaired.status_code == 200
    assert planner.full_repair_called is False
    assert planner.repair_attempts == 2


def test_quality_rejection_is_repaired_within_the_same_request(tmp_path: Path) -> None:
    client = _course_client(tmp_path)
    planner = _QualityRetryPlanner()
    client.app.state.course_planner = planner
    path = "/admin/courses/targeted-repair/lectures/lecture-01/canvas/draft"

    failed = client.post(
        path,
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "targeted-quality-failure-0001",
        },
    )
    repaired = client.post(
        f"{path}/repair",
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "targeted-quality-success-0001",
        },
    )

    assert failed.status_code == 503
    assert repaired.status_code == 200
    assert planner.quality_review_calls == 2
    assert len(planner.targeted_repair_calls) == 2
    assert "depends on an omitted exercise table" in planner.targeted_repair_calls[1][2]


def test_repairs_every_distinct_quality_issue_without_a_fixed_attempt_cap(tmp_path: Path) -> None:
    client = _course_client(tmp_path)
    planner = _ManyQualityRetryPlanner()
    client.app.state.course_planner = planner
    path = "/admin/courses/targeted-repair/lectures/lecture-01/canvas/draft"

    failed = client.post(
        path,
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "targeted-many-quality-failure-0001",
        },
    )
    repaired = client.post(
        f"{path}/repair",
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "targeted-many-quality-success-0001",
        },
    )

    assert failed.status_code == 503
    assert repaired.status_code == 200
    assert len(planner.targeted_repair_calls) == 5


class _TransientRepairPlanner(_TargetedRepairPlanner):
    def __init__(self) -> None:
        super().__init__()
        self.repair_attempts = 0

    async def repair_section(self, *args, **kwargs):
        self.repair_attempts += 1
        if self.repair_attempts == 1:
            raise ModelExecutionError("Course planner model request failed.")
        return await super().repair_section(*args, **kwargs)


class _QualityRetryPlanner(_TargetedRepairPlanner):
    async def validate_quality(self, source_document, candidate_document) -> None:
        self.quality_review_calls += 1
        if self.quality_review_calls == 1:
            raise CanvasGenerationRepairableError(
                "Canvas quality review failed: checkpoint depends on an omitted exercise table.",
                candidate=candidate_document,
                section_id="learning-optimization",
                block_id="optimization-math",
            )


class _ManyQualityRetryPlanner(_TargetedRepairPlanner):
    async def validate_quality(self, source_document, candidate_document) -> None:
        self.quality_review_calls += 1
        if self.quality_review_calls > 4:
            return
        block_id = f"optimization-issue-{self.quality_review_calls}"
        candidate_document.sections[0].blocks[0].id = block_id
        raise CanvasGenerationRepairableError(
            f"Canvas quality review failed: issue {self.quality_review_calls}.",
            candidate=candidate_document,
            section_id="learning-optimization",
            block_id=block_id,
        )

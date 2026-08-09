from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from auth_helpers import student_headers
from canvas_workspace_fixtures import published_course_canvas, write_course_source
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.models import (
    AgentCoachingContext,
    AgentTurnResult,
    QualityGateDecision,
    QualityGateStatus,
)
from lecturepilot.scaffold_policy import scaffold_policy_for_tutor_turn
from lecturepilot.storage_layout import StorageLayout

IDS = {"user_id": "student-1", "course_id": "course-1", "lecture_id": "lecture-1"}


def test_attempt_index_reaches_202_after_turn_history_rollover(tmp_path) -> None:
    store = CoachingProgressStore(StorageLayout(tmp_path))
    initial = _context(store)
    store.record_turn(
        **IDS,
        context=initial,
        policy=_policy(initial),
        decision=_decision(QualityGateStatus.NOT_ASSESSED, next_prompt="Try gate 1."),
        gate_revision="revision-1",
    )
    for _ in range(202):
        context = _context(store)
        event = store.record_turn(
            **IDS,
            context=context,
            policy=_policy(context),
            decision=_decision(QualityGateStatus.NEEDS_EVIDENCE, next_prompt="Try again."),
            gate_revision="revision-1",
        )

    progress = store.read(**IDS)
    assert len(progress.turns) == 200
    assert event.attempt_index == 202
    assert progress.attempt_counts == {"gate-1": 202}


def test_failed_delayed_attempt_becomes_supported_retry(tmp_path) -> None:
    started = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)
    store = CoachingProgressStore(StorageLayout(tmp_path))
    _pass_gate(store, started)
    due_at = started + timedelta(days=3)
    due = _context(store, now=due_at)
    store.record_turn(
        **IDS,
        context=due,
        policy=_policy(due),
        decision=_decision(QualityGateStatus.NOT_ASSESSED, next_prompt="Apply it to case B."),
        gate_revision="revision-1",
        now=due_at,
    )
    delayed = _context(store, now=due_at + timedelta(minutes=5))
    delayed_event = store.record_turn(
        **IDS,
        context=delayed,
        policy=_policy(delayed),
        decision=_decision(QualityGateStatus.NEEDS_EVIDENCE, next_prompt="Check the boundary."),
        gate_revision="revision-1",
        now=due_at + timedelta(minutes=5),
    )

    retry = _context(store, now=due_at + timedelta(minutes=6))
    retry_policy = _policy(retry)
    retry_event = store.record_turn(
        **IDS,
        context=retry,
        policy=retry_policy,
        decision=_decision(QualityGateStatus.PASSED),
        gate_revision="revision-1",
        now=due_at + timedelta(minutes=6),
    )

    review = store.read(**IDS).delayed_reviews["gate-1"]
    assert delayed_event.attempt_kind == "delayed_transfer"
    assert retry.delayed_transfer_due is False
    assert retry.pending_check_kind == "standard"
    assert retry.last_assistance_level == "cue"
    assert retry_policy.assistance_level == "cue"
    assert retry_event.attempt_kind == "supported_retry"
    assert review.attempted_at is not None
    assert review.completed_at is not None


def test_absent_attendance_is_only_the_initial_lecture_prior(tmp_path) -> None:
    app = create_app()
    app.state.canvas_workspace = _two_gate_workspace(tmp_path)
    harness = _PolicyHarness()
    app.state.agent_harness = harness
    client = TestClient(app)
    payload = {
        "course_id": "martius-ml",
        "lecture_id": "lecture-01",
        "attendance": "absent",
        "message": "Start the check.",
        "requested_gate_id": "gate-1",
    }

    first = client.post("/agent/turn", headers=student_headers("student-1"), json=payload)
    payload["requested_gate_id"] = "gate-2"
    second = client.post("/agent/turn", headers=student_headers("student-1"), json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert harness.assistance_levels == ["worked_step", "prompt"]


def _pass_gate(store, now: datetime) -> None:
    initial = _context(store, now=now)
    store.record_turn(
        **IDS,
        context=initial,
        policy=_policy(initial).model_copy(update={"assistance_level": "none"}),
        decision=_decision(QualityGateStatus.NOT_ASSESSED, next_prompt="Answer gate 1."),
        gate_revision="revision-1",
        now=now,
    )
    attempt = _context(store, now=now)
    store.record_turn(
        **IDS,
        context=attempt,
        policy=_policy(attempt),
        decision=_decision(QualityGateStatus.PASSED),
        gate_revision="revision-1",
        now=now,
    )


def _context(store, *, gate_id="gate-1", revision="revision-1", now=None):
    return store.context(
        **IDS,
        gate_id=gate_id,
        gate_title=gate_id,
        gate_revision=revision,
        now=now,
    )


def _policy(context: AgentCoachingContext, *, attendance="present"):
    return scaffold_policy_for_tutor_turn(
        attendance=attendance,
        delayed_transfer_due=context.delayed_transfer_due,
        last_gate_status=context.last_gate_status,
        needs_evidence_count=context.needs_evidence_count,
        prior_assistance=context.prior_assistance
        or getattr(context, "attendance_prior_used", False),
    )


def _decision(status, *, next_prompt=None):
    return QualityGateDecision(
        gate_id="gate-1",
        status=status,
        reason="test",
        next_prompt=next_prompt,
    )


def _two_gate_workspace(tmp_path) -> CanvasWorkspace:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=write_course_source(tmp_path),
    )
    document = published_course_canvas("martius-ml", "lecture-01")
    section = document.sections[0]
    document.sections[0] = section.model_copy(
        update={
            "blocks": [
                *section.blocks,
                CanvasBlock(id="gate-1", type="checkpoint", text="Explain gate one."),
                CanvasBlock(id="gate-2", type="checkpoint", text="Explain gate two."),
            ]
        }
    )
    workspace.write_course_canvas(document)
    return workspace


class _PolicyHarness:
    def __init__(self) -> None:
        self.assistance_levels: list[str] = []

    async def run_turn(self, turn, **_kwargs) -> AgentTurnResult:
        self.assistance_levels.append(turn.scaffold_policy.assistance_level)
        return AgentTurnResult(message="Continue.", model="test-harness")

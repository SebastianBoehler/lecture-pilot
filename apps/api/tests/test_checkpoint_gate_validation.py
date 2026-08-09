from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.coaching_state_models import CoachingProgress, DelayedReview
from lecturepilot.durable_files import atomic_write_json
from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    Course,
    CourseWorkspaceResult,
    Lecture,
    QualityGateDecision,
    QualityGateStatus,
)


def test_requested_checkpoint_must_belong_to_focused_published_section(tmp_path: Path) -> None:
    client, harness = _client(tmp_path)
    body = {
        "course_id": "checkpoint-course",
        "lecture_id": "lecture-01",
        "attendance": "present",
        "message": "My explanation",
        "canvas_state": {"focused_section_id": "concept-a"},
    }

    unknown = client.post(
        "/agent/turn",
        headers=student_headers("student-a", course_ids=["checkpoint-course"]),
        json={**body, "checkpoint_gate_id": "invented-gate"},
    )
    wrong_section = client.post(
        "/agent/turn",
        headers=student_headers("student-a", course_ids=["checkpoint-course"]),
        json={**body, "checkpoint_gate_id": "concept-b-check"},
    )

    assert unknown.status_code == 400
    assert unknown.json()["detail"] == "Requested checkpoint is not in the published learning map."
    assert wrong_section.status_code == 400
    assert (
        wrong_section.json()["detail"]
        == "Requested checkpoint does not belong to the focused section."
    )
    assert harness.turns == []


def test_valid_requested_checkpoint_reaches_tutor_with_exact_gate_id(tmp_path: Path) -> None:
    client, harness = _client(tmp_path)

    response = client.post(
        "/agent/turn",
        headers=student_headers("student-a", course_ids=["checkpoint-course"]),
        json={
            "course_id": "checkpoint-course",
            "lecture_id": "lecture-01",
            "attendance": "present",
            "message": "My explanation",
            "checkpoint_gate_id": "concept-a-check",
            "canvas_state": {"focused_section_id": "concept-a"},
        },
    )

    assert response.status_code == 200
    assert harness.turns[0].active_gate.id == "concept-a-check"


def test_requested_checkpoint_takes_priority_over_a_different_due_review(tmp_path: Path) -> None:
    client, harness = _client(tmp_path)
    learning_map = client.app.state.canvas_workspace.course_canvas_store.learning_map(
        course_id="checkpoint-course", lecture_id="lecture-01"
    )
    due_gate = next(gate for gate in learning_map.gates if gate.id == "concept-b-check")
    now = datetime.now(UTC)
    progress = CoachingProgress(
        delayed_reviews={
            due_gate.id: DelayedReview(
                gate_id=due_gate.id,
                gate_revision=due_gate.revision,
                scheduled_at=(now - timedelta(days=3)).isoformat(),
                due_at=(now - timedelta(days=1)).isoformat(),
            )
        }
    )
    path = (
        client.app.state.canvas_workspace.layout.user_lecture_root(
            "student-a", "checkpoint-course", "lecture-01"
        )
        / "tutor-state.json"
    )
    atomic_write_json(path, progress.model_dump(mode="json"))

    response = client.post(
        "/agent/turn",
        headers=student_headers("student-a", course_ids=["checkpoint-course"]),
        json={
            "course_id": "checkpoint-course",
            "lecture_id": "lecture-01",
            "attendance": "present",
            "message": "My inline answer",
            "checkpoint_gate_id": "concept-a-check",
            "canvas_state": {"focused_section_id": "concept-a"},
        },
    )

    assert response.status_code == 200
    assert harness.turns[0].active_gate.id == "concept-a-check"


def test_inline_checkpoint_without_matching_pending_episode_cannot_auto_pass(
    tmp_path: Path,
) -> None:
    client, _ = _client(tmp_path, harness=_PassingHarness())

    response = client.post(
        "/agent/turn",
        headers=student_headers("student-a", course_ids=["checkpoint-course"]),
        json={
            "course_id": "checkpoint-course",
            "lecture_id": "lecture-01",
            "attendance": "present",
            "message": "My inline answer",
            "requested_gate_id": "concept-a-check",
            "canvas_state": {"focused_section_id": "concept-a"},
        },
    )

    assert response.status_code == 200
    assert response.json()["quality_gate"]["status"] == "not_assessed"


def test_valid_inline_checkpoint_is_bound_as_an_independent_assessed_attempt(
    tmp_path: Path,
) -> None:
    client, _ = _client(tmp_path, harness=_PassingHarness())

    response = client.post(
        "/agent/turn",
        headers=student_headers("student-a", course_ids=["checkpoint-course"]),
        json={
            "course_id": "checkpoint-course",
            "lecture_id": "lecture-01",
            "attendance": "present",
            "message": "My inline answer",
            "checkpoint_gate_id": "concept-a-check",
            "canvas_state": {"focused_section_id": "concept-a"},
        },
    )

    assert response.status_code == 200
    assert response.json()["quality_gate"]["status"] == "passed"
    events = client.app.state.analytics_store.events(
        course_id="checkpoint-course", lecture_id="lecture-01"
    )
    assert events[0]["gate_id"] == "concept-a-check"
    assert events[0]["attempt_kind"] == "independent"
    assert events[0]["attempt_index"] == 1


def _client(tmp_path: Path, harness=None) -> tuple[TestClient, "_Harness"]:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    write_course_workspace(
        app.state.canvas_workspace.course_media_root("checkpoint-course"),
        CourseWorkspaceResult(
            course=Course(
                id="checkpoint-course", title="Checkpoint", professor="Professor", term="2026"
            ),
            lectures=[
                Lecture(
                    id="lecture-01",
                    course_id="checkpoint-course",
                    title="Concepts",
                    date=date(2020, 1, 1),
                )
            ],
            active_lecture_id="lecture-01",
        ),
    )
    app.state.canvas_workspace.write_course_canvas(
        CanvasDocument(
            id="checkpoint-course-lecture-01",
            course_id="checkpoint-course",
            lecture_id="lecture-01",
            title="Concepts",
            source_kind="generated",
            source_ref="test",
            workspace_path="course/index.md",
            sections=[
                _section("concept-a", "concept-a-check"),
                _section("concept-b", "concept-b-check"),
            ],
        )
    )
    harness = harness or _Harness()
    app.state.agent_harness = harness
    return TestClient(app), harness


def _section(section_id: str, gate_id: str) -> CanvasSection:
    return CanvasSection(
        id=section_id,
        title=section_id,
        blocks=[CanvasBlock(id=gate_id, type="checkpoint", text="Explain the concept.")],
    )


class _Harness:
    def __init__(self) -> None:
        self.turns: list[AgentTurnInput] = []

    async def run_turn(self, turn: AgentTurnInput) -> AgentTurnResult:
        self.turns.append(turn)
        return AgentTurnResult(message="Tutor feedback", quality_gate=None, model="test-model")


class _PassingHarness(_Harness):
    async def run_turn(self, turn: AgentTurnInput) -> AgentTurnResult:
        self.turns.append(turn)
        return AgentTurnResult(
            message="Pass claimed.",
            quality_gate=QualityGateDecision(
                gate_id=turn.active_gate.id,
                gate_revision=turn.active_gate.revision,
                status=QualityGateStatus.PASSED,
                reason="Claimed pass.",
                evidence_ids=[turn.active_gate.id],
            ),
            model="test-model",
        )

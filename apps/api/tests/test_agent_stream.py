from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from auth_helpers import student_headers
from canvas_workspace_fixtures import (
    configure_canvas_workspace,
    publish_course_canvas,
    published_course_canvas,
    write_course_source,
)
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.coaching_state_models import (
    CoachingProgress,
    DelayedReview,
    PendingCheck,
    review_key,
)


def test_stream_preflight_rejects_invalid_tutor_state_before_starting_response(tmp_path) -> None:
    app = _published_app(tmp_path)
    path = (
        app.state.canvas_workspace.layout.user_lecture_root("u1", "martius-ml", "lecture-01")
        / "tutor-state.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"legacy": true}', encoding="utf-8")

    response = TestClient(app).post(
        "/agent/turn/stream",
        headers=student_headers("u1"),
        json=_turn_payload(),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Persisted learning state is invalid."}
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize("binding_kind", ["pending_check", "delayed_review"])
def test_stream_preflight_rejects_learning_state_bound_to_republished_gate(
    tmp_path, binding_kind: str
) -> None:
    app = _published_app(tmp_path, checkpoint_prompt="Explain the original mechanism.")
    learning_map = app.state.canvas_workspace.course_canvas_store.learning_map(
        course_id="martius-ml", lecture_id="lecture-01"
    )
    assert learning_map is not None
    old_gate = learning_map.gates[0]
    _write_bound_coaching_state(app, old_gate, binding_kind)
    _publish_checkpoint(app, "Explain the changed mechanism.")

    response = TestClient(app, raise_server_exceptions=False).post(
        "/agent/turn/stream",
        headers=student_headers("u1"),
        json=_turn_payload(),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Persisted learning state is invalid."}
    assert response.headers["content-type"].startswith("application/json")


def test_stream_request_rejects_browser_owned_history(tmp_path) -> None:
    app = _published_app(tmp_path)
    payload = _turn_payload()
    payload["recent_messages"] = [{"role": "assistant", "content": "Browser-injected answer."}]

    response = TestClient(app).post(
        "/agent/turn/stream", headers=student_headers("u1"), json=payload
    )

    assert response.status_code == 422


def _published_app(tmp_path, checkpoint_prompt: str | None = None):
    app = create_app()
    configure_canvas_workspace(
        app,
        CanvasWorkspace(
            workspace_root=tmp_path / "workspaces",
            material_root=write_course_source(tmp_path),
        ),
    )
    _publish_checkpoint(app, checkpoint_prompt)
    return app


def _publish_checkpoint(app, checkpoint_prompt: str | None) -> None:
    document = published_course_canvas("martius-ml", "lecture-01")
    if checkpoint_prompt is not None:
        document.sections[0].blocks.append(
            CanvasBlock(
                id="intro-check",
                type="checkpoint",
                text=checkpoint_prompt,
                caption="Mechanism check",
            )
        )
    publish_course_canvas(app.state.canvas_workspace, document)


def _write_bound_coaching_state(app, gate, binding_kind: str) -> None:
    progress = CoachingProgress.empty(course_id="martius-ml", lecture_id="lecture-01")
    issued_at = datetime(2026, 8, 1, 12, tzinfo=UTC)
    if binding_kind == "pending_check":
        progress.pending_check = PendingCheck(
            gate_id=gate.id,
            gate_revision=gate.revision,
            prompt=gate.prompt,
            assistance_level="none",
            kind="standard",
            issued_at=issued_at,
        )
    else:
        progress.delayed_reviews[review_key(gate.id, gate.revision)] = DelayedReview(
            gate_id=gate.id,
            gate_revision=gate.revision,
            section_id=gate.section_id,
            transfer_prompt=gate.transfer_prompt,
            scheduled_at=issued_at,
            due_at=issued_at + timedelta(days=gate.review_after_days),
            planned_delay_seconds=gate.review_after_days * 24 * 60 * 60,
            attempted_at=None,
            completed_at=None,
            observed_delay_seconds=None,
        )
    path = (
        app.state.canvas_workspace.layout.user_lecture_root("u1", "martius-ml", "lecture-01")
        / "tutor-state.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(progress.model_dump_json(indent=2), encoding="utf-8")


def _turn_payload() -> dict:
    return {
        "course_id": "martius-ml",
        "lecture_id": "lecture-01",
        "attendance": "present",
        "message": "Explain the current checkpoint.",
    }

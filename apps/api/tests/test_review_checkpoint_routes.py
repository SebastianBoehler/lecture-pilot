import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from auth_helpers import student_headers
from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.coaching_state_models import PendingCheck
from lecturepilot.model_payload import agent_result_from_content
from test_agent_stream import _published_app
from canvas_workspace_fixtures import publish_course_canvas, published_course_canvas
from lecturepilot.canvas_models import CanvasBlock


class Assessor:
    def __init__(self, passed=False):
        self.passed = passed

    async def run_turn(self, turn, **kwargs):
        gate = turn.active_gate
        section = next(
            section for section in turn.canvas_context.sections if section.id == gate.section_id
        )
        ids = [criterion.id for criterion in gate.evidence_criteria] if self.passed else []
        commands = [
            {
                "type": name,
                "section_id": section.id,
                "span_id": section.blocks[0].id if name == "highlight_span" else None,
                "highlight_text": None,
                "artifact_id": None,
                "section": None,
                "placement": None,
            }
            for name in ("focus_section", "highlight_span")
        ]
        return agent_result_from_content(
            json.dumps(
                {
                    "message": "Feedback",
                    "session_goal": None,
                    "canvas_commands": commands,
                    "assessment": {
                        "gate_id": gate.id,
                        "gate_revision": gate.revision,
                        "reason": "Checked criteria",
                        "evidence_ids": ids,
                        "evidence_quotes": [
                            {"evidence_id": identity, "quote": turn.message} for identity in ids
                        ],
                    },
                }
            ),
            turn,
            "test-model",
        )


def setup(tmp_path):
    app = _published_app(tmp_path, checkpoint_prompt="Explain the cause and its effect.")
    gate = app.state.canvas_workspace.course_canvas_store.learning_map(
        course_id="martius-ml", lecture_id="lecture-01"
    ).gates[0]
    assert not gate.hint_ladder and gate.practice_target_id is None
    ids = dict(user_id="u1", course_id="martius-ml", lecture_id="lecture-01")
    payload = {
        "course_id": "martius-ml",
        "lecture_id": "lecture-01",
        "attendance": "present",
        "checkpoint_gate_id": gate.id,
        "canvas_state": {"focused_section_id": gate.section_id},
    }
    return TestClient(app), gate, ids, payload


def test_wrong_plain_checkpoint_can_be_retried_and_passed_through_the_api(tmp_path):
    client, gate, ids, payload = setup(tmp_path)
    grader = client.app.state.agent_harness = Assessor()
    response = client.post(
        "/agent/turn", headers=student_headers("u1"), json={**payload, "message": "Partial answer."}
    )
    assert response.status_code == 200, response.text
    assert response.json()["quality_gate"]["status"] == "needs_evidence"
    store = CoachingProgressStore(client.app.state.canvas_workspace.layout)
    assert not store.read(**ids).pending_check.support_exhausted
    grader.passed = True
    retry = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json={**payload, "message": "The cause produces an observable effect."},
    )
    assert retry.status_code == 200, retry.text
    assert retry.json()["quality_gate"]["status"] == "passed"
    assert store.read(**ids).pending_check is None
    assert store.read(**ids).goal_evidence[f"{gate.id}@{gate.revision}"].independent


def test_saved_false_exhaustion_is_corrected_on_reload_and_submission(tmp_path):
    client, gate, ids, payload = setup(tmp_path)
    store = CoachingProgressStore(client.app.state.canvas_workspace.layout)
    client.app.state.agent_harness = Assessor()
    result = client.post(
        "/agent/turn", headers=student_headers("u1"), json={**payload, "message": "Partial answer."}
    )
    assert result.status_code == 200
    progress = store.read(**ids)
    progress.pending_check = PendingCheck(
        **{
            **progress.pending_check.model_dump(),
            "stage": "exit_support",
            "bank_exhausted": True,
            "support_exhausted": True,
            "issued_at": datetime.now(UTC),
        }
    )
    key = f"{gate.id}@{gate.revision}@independent-exit"
    progress.task_exposures[key] = progress.task_exposures[key].model_copy(
        update={"supported": True}
    )
    store._write(**ids, progress=progress)
    state = client.get(
        "/courses/martius-ml/lectures/lecture-01/learner-state", headers=student_headers("u1")
    )
    assert state.status_code == 200, state.text
    assert state.json()["pending_check"]["stage"] == "independent_exit"
    assert not state.json()["pending_check"]["support_exhausted"]
    retry = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json={**payload, "message": "Another partial answer."},
    )
    assert retry.status_code == 200, retry.text
    client.app.state.agent_harness = Assessor(passed=True)
    result = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json={**payload, "message": "The cause produces an observable effect."},
    )
    assert result.status_code == 200, result.text
    assert store.read(**ids).pending_check is None
    assert not store.read(**ids).task_exposures[key].supported


def test_chat_cannot_persist_a_gate_pass_even_when_a_check_is_pending(tmp_path):
    client, gate, ids, payload = setup(tmp_path)
    store = CoachingProgressStore(client.app.state.canvas_workspace.layout)
    store.bind_inline_checkpoint(**ids, gate=gate)
    client.app.state.agent_harness = Assessor(passed=True)
    del payload["checkpoint_gate_id"]
    result = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json={**payload, "message": "The cause produces an observable effect."},
    )
    assert result.status_code == 503
    assert not store.read(**ids).turns
    assert not client.app.state.learner_state.latest_gate_decisions(**ids)


def test_another_checkpoint_cannot_replace_the_pending_check(tmp_path):
    client, _, ids, payload = setup(tmp_path)
    document = published_course_canvas("martius-ml", "lecture-01")
    document.sections[0].blocks.extend(
        [
            CanvasBlock(id="first-check", type="checkpoint", text="Explain the first cause."),
            CanvasBlock(id="second-check", type="checkpoint", text="Explain the second cause."),
        ]
    )
    publish_course_canvas(client.app.state.canvas_workspace, document)
    gates = client.app.state.canvas_workspace.course_canvas_store.learning_map(
        course_id="martius-ml", lecture_id="lecture-01"
    ).gates
    store = CoachingProgressStore(client.app.state.canvas_workspace.layout)
    store.bind_inline_checkpoint(**ids, gate=gates[0])

    class NoCall:
        async def run_turn(self, *args, **kwargs):
            raise AssertionError(
                "A different pending gate must be rejected before model execution."
            )

    client.app.state.agent_harness = NoCall()
    result = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json={
            **payload,
            "checkpoint_gate_id": gates[1].id,
            "message": "The second cause has an effect.",
        },
    )
    assert result.status_code == 409, result.text
    assert store.read(**ids).pending_check.gate_id == gates[0].id


def test_profile_requires_every_current_published_gate_to_pass(tmp_path):
    client, gate, ids, _ = setup(tmp_path)
    root = client.app.state.canvas_workspace.layout.user_lecture_root(
        "u1", "martius-ml", "lecture-01"
    )
    root.mkdir(parents=True, exist_ok=True)
    document = published_course_canvas("martius-ml", "lecture-01")
    document.sections[0].blocks.extend(
        [
            CanvasBlock(id="first-check", type="checkpoint", text="Explain the first cause."),
            CanvasBlock(id="second-check", type="checkpoint", text="Explain the second cause."),
        ]
    )
    publish_course_canvas(client.app.state.canvas_workspace, document)
    gates = client.app.state.canvas_workspace.course_canvas_store.learning_map(
        course_id=ids["course_id"], lecture_id=ids["lecture_id"]
    ).gates
    records = {gates[0].id: {"status": "passed", "gate_revision": gates[0].revision}}

    def passed():
        (root / "gates.json").write_text(json.dumps({"gates": records}))
        result = client.get("/me/learning-profile", headers=student_headers("u1"))
        assert result.status_code == 200, result.text
        return result.json()["courses"][0]["passed_lecture_ids"]

    assert passed() == []
    records.update(
        {gate.id: {"status": "passed", "gate_revision": gate.revision} for gate in gates}
    )
    records[gates[-1].id]["gate_revision"] = "stale"
    assert passed() == []
    records[gates[-1].id]["gate_revision"] = gates[-1].revision
    assert passed() == ["lecture-01"]

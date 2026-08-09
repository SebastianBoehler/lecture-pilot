from datetime import timedelta
from pathlib import Path

from auth_helpers import professor_headers, student_headers
from lecturepilot.coaching_assistance import NextCheck, NextCheckAssistance
from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.coaching_state_models import review_key
from lecturepilot.models import QualityGateDecision
from lecturepilot.quality_gate_models import QualityGateStatus
from lecturepilot.scaffold_policy import scaffold_policy_for_tutor_turn
from review_queue_test_helpers import (
    COURSE_ID,
    NOW,
    gate_revision as _gate_revision,
    read_progress as _read_progress,
    review_client as _client,
    write_progress as _write_progress,
    write_readiness_task as _write_readiness_task,
    write_review as _write_review,
)


def test_review_queue_orders_due_gates_then_repairs_without_answer_text(tmp_path: Path) -> None:
    client = _client(tmp_path)
    user_id = "student-a"
    _write_review(client, user_id, "lecture-b", "gate-b", NOW - timedelta(days=2))
    _write_review(client, user_id, "lecture-a", "gate-a", NOW - timedelta(days=1))
    _write_review(client, user_id, "lecture-a", "gate-c", NOW - timedelta(days=1))
    _write_readiness_task(client, user_id)

    response = client.get(
        f"/courses/{COURSE_ID}/review-queue",
        headers=student_headers(user_id, course_ids=[COURSE_ID]),
    )

    assert response.status_code == 200
    payload = response.json()
    assert [(item["kind"], item["id"]) for item in payload["items"]] == [
        ("gate_review", "gate:lecture-b:gate-b"),
        ("gate_review", "gate:lecture-a:gate-a"),
        ("gate_review", "gate:lecture-a:gate-c"),
        ("readiness_repair", "readiness:repair-risk"),
    ]
    serialized = response.text
    assert "wrong learner answer" not in serialized
    assert "Name the hidden answer" not in serialized
    assert "Which hidden option" not in serialized
    assert _read_progress(client, user_id, "lecture-a").pending_check is None


def test_review_queue_is_user_course_and_access_isolated(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _write_review(client, "student-a", "lecture-a", "gate-a", NOW - timedelta(days=1))
    _write_readiness_task(client, "student-a", course_id="other-course")
    url = f"/courses/{COURSE_ID}/review-queue"

    own = client.get(url, headers=student_headers("student-a", course_ids=[COURSE_ID]))
    other = client.get(
        f"{url}?user_id=student-a",
        headers=student_headers("student-b", course_ids=[COURSE_ID]),
    )
    unenrolled = client.get(url, headers=student_headers("outsider", course_ids=[]))
    professor = client.get(url, headers=professor_headers("prof-a"))
    preview = client.get(
        url,
        headers={**professor_headers("prof-a"), "X-LecturePilot-Learner-Preview": "professor"},
    )

    assert own.status_code == 200
    assert len(own.json()["items"]) == 1
    assert other.status_code == 200
    assert other.json()["items"] == []
    assert unenrolled.status_code == 404
    assert professor.status_code == 403
    assert preview.status_code == 403


def test_open_due_gate_binds_exact_current_transfer_without_completing(tmp_path: Path) -> None:
    client = _client(tmp_path)
    user_id = "student-a"
    due_at = NOW - timedelta(days=1)
    _write_review(client, user_id, "lecture-a", "gate-a", due_at)

    response = client.post(
        f"/courses/{COURSE_ID}/review-queue/gates/lecture-a/gate-a/open",
        headers=student_headers(user_id, course_ids=[COURSE_ID]),
    )

    assert response.status_code == 200
    assert response.json() == {
        "course_id": COURSE_ID,
        "lecture_id": "lecture-a",
        "section_id": "section-a",
        "gate_id": "gate-a",
        "gate_revision": _gate_revision(client, "lecture-a", "gate-a"),
        "prompt": "Apply A to an unfamiliar case.",
        "stage": "due",
    }
    progress = _read_progress(client, user_id, "lecture-a")
    assert progress.pending_check is not None
    assert progress.pending_check.prompt == "Apply A to an unfamiliar case."
    assert progress.pending_check.assistance_level == "none"
    assert progress.pending_check.kind == "delayed_transfer"
    key = review_key("gate-a", _gate_revision(client, "lecture-a", "gate-a"))
    assert progress.delayed_reviews[key].attempted_at is None
    assert progress.delayed_reviews[key].completed_at is None


def test_failed_due_attempt_becomes_repair_and_pass_clears_only_that_review(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    user_id = "student-a"
    _write_review(client, user_id, "lecture-a", "gate-a", NOW - timedelta(days=2))
    _write_review(client, user_id, "lecture-b", "gate-b", NOW - timedelta(days=1))
    _write_readiness_task(client, user_id)
    headers = student_headers(user_id, course_ids=[COURSE_ID])
    open_url = f"/courses/{COURSE_ID}/review-queue/gates/lecture-a/gate-a/open"
    assert client.post(open_url, headers=headers).status_code == 200
    store = CoachingProgressStore(client.app.state.canvas_workspace.layout)
    revision = _gate_revision(client, "lecture-a", "gate-a")
    context = store.context(
        user_id=user_id,
        course_id=COURSE_ID,
        lecture_id="lecture-a",
        gate_id="gate-a",
        gate_revision=revision,
        learning_objective="Explain and apply gate A.",
        now=NOW,
    )
    policy = scaffold_policy_for_tutor_turn(
        attendance="present",
        delayed_transfer_due=True,
        last_gate_status=None,
        needs_evidence_count=0,
        prior_assistance=False,
    )
    store.record_turn(
        user_id=user_id,
        course_id=COURSE_ID,
        lecture_id="lecture-a",
        context=context,
        policy=policy,
        decision=QualityGateDecision(
            gate_id="gate-a",
            gate_revision=revision,
            status=QualityGateStatus.NEEDS_EVIDENCE,
            reason="Apply the mechanism, not the memorized wording.",
            evidence_ids=[],
            missing_evidence_ids=["gate-a"],
        ),
        next_check=NextCheck(
            gate_id="gate-a",
            gate_revision=revision,
            prompt="Apply A to an unfamiliar case.",
            assistance=NextCheckAssistance(level="none", content=None),
        ),
        gate_section_id="section-a",
        transfer_prompt="Apply A to an unfamiliar case.",
        review_after_days=2,
        user_message="Attempt",
        assistant_message="Try the current check again.",
        now=NOW + timedelta(minutes=2),
    )

    failed_queue = client.get(
        f"/courses/{COURSE_ID}/review-queue",
        headers=headers,
    ).json()["items"]
    assert [(item["kind"], item["id"]) for item in failed_queue] == [
        ("gate_review", "gate:lecture-b:gate-b"),
        ("gate_repair", "gate-repair:lecture-a:gate-a"),
        ("readiness_repair", "readiness:repair-risk"),
    ]
    repair_opening = client.post(open_url, headers=headers)
    assert repair_opening.status_code == 200
    assert repair_opening.json()["stage"] == "repair"
    assert repair_opening.json()["prompt"] == "Apply A to an unfamiliar case."

    repair_context = store.context(
        user_id=user_id,
        course_id=COURSE_ID,
        lecture_id="lecture-a",
        gate_id="gate-a",
        gate_revision=revision,
        learning_objective="Explain and apply gate A.",
        now=NOW + timedelta(minutes=4),
    )
    store.record_turn(
        user_id=user_id,
        course_id=COURSE_ID,
        lecture_id="lecture-a",
        context=repair_context,
        policy=policy,
        decision=QualityGateDecision(
            gate_id="gate-a",
            gate_revision=revision,
            status=QualityGateStatus.PASSED,
            reason="The changed case is explained.",
            evidence_ids=["gate-a"],
            missing_evidence_ids=[],
        ),
        next_check=None,
        gate_section_id="section-a",
        transfer_prompt="Apply A to an unfamiliar case.",
        review_after_days=2,
        user_message="Repair",
        assistant_message="Passed.",
        now=NOW + timedelta(minutes=5),
    )
    final_items = client.get(
        f"/courses/{COURSE_ID}/review-queue",
        headers=headers,
    ).json()["items"]
    assert [item["id"] for item in final_items] == [
        "gate:lecture-b:gate-b",
        "readiness:repair-risk",
    ]


def test_open_rejects_locked_stale_and_wrong_gate_targets(tmp_path: Path) -> None:
    client = _client(tmp_path)
    user_id = "student-a"
    headers = student_headers(user_id, course_ids=[COURSE_ID])
    _write_review(client, user_id, "lecture-a", "gate-a", NOW - timedelta(days=1))
    _write_review(client, user_id, "lecture-locked", "gate-locked", NOW - timedelta(days=1))
    progress = _read_progress(client, user_id, "lecture-a")
    current_revision = _gate_revision(client, "lecture-a", "gate-a")
    key = review_key("gate-a", current_revision)
    progress.delayed_reviews[key] = progress.delayed_reviews[key].model_copy(
        update={"gate_revision": "stale-revision"}
    )
    _write_progress(client, user_id, "lecture-a", progress)

    stale = client.post(
        f"/courses/{COURSE_ID}/review-queue/gates/lecture-a/gate-a/open",
        headers=headers,
    )
    wrong = client.post(
        f"/courses/{COURSE_ID}/review-queue/gates/lecture-a/gate-b/open",
        headers=headers,
    )
    locked = client.post(
        f"/courses/{COURSE_ID}/review-queue/gates/lecture-locked/gate-locked/open",
        headers=headers,
    )
    unpublished_response = client.post(
        f"/courses/{COURSE_ID}/review-queue/gates/lecture-unpublished/gate-unpublished/open",
        headers=headers,
    )

    assert stale.status_code == 409
    assert wrong.status_code == 404
    assert locked.status_code == 403
    assert unpublished_response.status_code == 404

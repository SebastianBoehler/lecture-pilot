from pathlib import Path

from auth_helpers import confirm_source_routing, professor_headers, student_headers
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.providers import ProviderConfigurationError
from practice_design_route_test_helpers import (
    COURSE_ID,
    ChangingPlanner as _ChangingPlanner,
    FailingPlanner as _FailingPlanner,
    FailingReviewPlanner as _FailingReviewPlanner,
    Planner as _Planner,
    client as _client,
    design_path as _design_path,
    proposal_path as _proposal_path,
)


def test_owner_can_propose_edit_and_approve_a_current_practice_design(tmp_path: Path) -> None:
    client = _client(tmp_path)
    planner = _Planner()
    client.app.state.practice_design_planner = planner

    proposed = client.post(_proposal_path(), headers=professor_headers())

    assert proposed.status_code == 200, proposed.json()
    design = proposed.json()
    routing_revision = client.get(
        f"/admin/courses/{COURSE_ID}/source-routing", headers=professor_headers()
    ).json()["source_revision"]
    assert design["source_revision"] != routing_revision
    proposed_readiness = client.get(f"{_design_path()}/readiness", headers=professor_headers())
    assert proposed_readiness.status_code == 200
    assert proposed_readiness.json() == {
        "lecture_id": "lecture-01",
        "current_source_revision": design["source_revision"],
        "practice_design_revision": design["revision"],
        "ready_for_generation": False,
    }
    assert design["quality_review"]["source_revision"] == design["source_revision"]
    assert design["quality_review"]["practice_design_revision"] == design["revision"]
    assert client.get(_design_path(), headers=student_headers()).status_code == 403
    assert client.post(_proposal_path(), headers=student_headers()).status_code == 403
    assert (
        client.put(
            _design_path(),
            headers=student_headers(),
            json={
                "source_revision": design["source_revision"],
                "practice_design_revision": design["revision"],
                "lecture_title": design["lecture_title"],
                "objective": design["objective"],
                "planning_context": design["planning_context"],
                "targets": design["targets"],
            },
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"{_design_path()}/review",
            headers=student_headers(),
            json={
                "source_revision": design["source_revision"],
                "practice_design_revision": design["revision"],
            },
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"{_design_path()}/approve",
            headers=student_headers(),
            json={
                "source_revision": design["source_revision"],
                "practice_design_revision": design["revision"],
            },
        ).status_code
        == 403
    )
    assert client.post(_proposal_path(), headers=professor_headers()).status_code == 200
    assert planner.calls == 1

    updated = client.put(
        _design_path(),
        headers=professor_headers(),
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
            "lecture_title": design["lecture_title"],
            "objective": "Calculate posterior probabilities from evidence.",
            "planning_context": design["planning_context"],
            "targets": design["targets"],
        },
    )

    assert updated.status_code == 200
    assert updated.json()["approval"] is None
    assert updated.json()["quality_review"] is None
    stale = client.put(
        _design_path(),
        headers=professor_headers(),
        json={
            "source_revision": updated.json()["source_revision"],
            "practice_design_revision": design["revision"],
            "lecture_title": updated.json()["lecture_title"],
            "objective": updated.json()["objective"],
            "planning_context": updated.json()["planning_context"],
            "targets": updated.json()["targets"],
        },
    )
    assert stale.status_code == 409
    stale_approval = client.post(
        f"{_design_path()}/approve",
        headers=professor_headers(),
        json={
            "source_revision": "b" * 64,
            "practice_design_revision": updated.json()["revision"],
        },
    )
    assert stale_approval.status_code == 409
    blocked = client.post(
        f"{_design_path()}/approve",
        headers=professor_headers(),
        json={
            "source_revision": updated.json()["source_revision"],
            "practice_design_revision": updated.json()["revision"],
        },
    )

    assert blocked.status_code == 409
    reviewed = client.post(
        f"{_design_path()}/review",
        headers=professor_headers(),
        json={
            "source_revision": updated.json()["source_revision"],
            "practice_design_revision": updated.json()["revision"],
        },
    )
    assert reviewed.status_code == 200
    assert (
        reviewed.json()["quality_review"]["practice_design_revision"] == updated.json()["revision"]
    )
    assert planner.review_calls == 1
    approved = client.post(
        f"{_design_path()}/approve",
        headers=professor_headers(),
        json={
            "source_revision": reviewed.json()["source_revision"],
            "practice_design_revision": reviewed.json()["revision"],
        },
    )

    assert approved.status_code == 200
    assert approved.json()["approval"]["practice_design_revision"] == updated.json()["revision"]
    approved_readiness = client.get(f"{_design_path()}/readiness", headers=professor_headers())
    assert approved_readiness.json()["ready_for_generation"] is True
    assert client.get(f"{_design_path()}/readiness", headers=student_headers()).status_code == 403
    changed_source = client.post(
        f"/admin/courses/{COURSE_ID}/materials",
        headers=professor_headers(),
        data={"path": "Lecture01-supplement.md"},
        files={"file": ("Lecture01-supplement.md", b"# Supplement\n\nNew posterior evidence.")},
    )
    assert changed_source.status_code == 200
    confirm_source_routing(client, COURSE_ID)
    stale_response = client.get(f"{_design_path()}/readiness", headers=professor_headers())
    assert stale_response.status_code == 200, stale_response.json()
    stale_readiness = stale_response.json()
    assert stale_readiness["current_source_revision"] != design["source_revision"]
    assert stale_readiness["ready_for_generation"] is False


def test_rejects_invalid_target_source_references(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.practice_design_planner = _Planner()
    design = client.post(_proposal_path(), headers=professor_headers()).json()
    target = design["targets"][0]
    target["source_refs"] = ["unrouted.md"]
    for field in (
        "outcome_anchor",
        "target_invariant_anchor",
        "baseline_task_anchor",
        "independent_exit_task_anchor",
        "delayed_transfer_task_anchor",
    ):
        target[field]["source_path"] = "unrouted.md"
    target["evidence_criteria"][0]["source_anchor"]["source_path"] = "unrouted.md"

    response = client.put(
        _design_path(),
        headers=professor_headers(),
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
            "lecture_title": design["lecture_title"],
            "objective": design["objective"],
            "planning_context": design["planning_context"],
            "targets": [target],
        },
    )

    assert response.status_code == 422
    assert "unrouted.md" in response.json()["detail"]


def test_critical_semantic_review_remains_visible_and_blocks_approval(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.practice_design_planner = _Planner(severity="critical")

    proposed = client.post(_proposal_path(), headers=professor_headers())

    assert proposed.status_code == 200
    design = proposed.json()
    assert design["quality_review"]["checks"][0]["severity"] == "critical"
    response = client.post(
        f"{_design_path()}/approve",
        headers=professor_headers(),
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
        },
    )
    assert response.status_code == 409
    assert "critical" in response.json()["detail"].lower()


def test_warning_semantic_review_remains_visible_and_allows_approval(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.practice_design_planner = _Planner(severity="warning")

    proposed = client.post(_proposal_path(), headers=professor_headers())

    assert proposed.status_code == 200
    design = proposed.json()
    assert design["quality_review"]["checks"][0]["severity"] == "warning"
    assert design["quality_review"]["checks"][0]["supporting_anchors"]
    approved = client.post(
        f"{_design_path()}/approve",
        headers=professor_headers(),
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
        },
    )
    assert approved.status_code == 200


def test_review_provider_failure_leaves_the_edited_design_unreviewed(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.practice_design_planner = _Planner()
    design = client.post(_proposal_path(), headers=professor_headers()).json()
    edited = client.put(
        _design_path(),
        headers=professor_headers(),
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
            "lecture_title": design["lecture_title"],
            "objective": "Calculate a revised posterior from stated evidence.",
            "planning_context": design["planning_context"],
            "targets": design["targets"],
        },
    ).json()
    client.app.state.practice_design_planner = _FailingReviewPlanner()

    response = client.post(
        f"{_design_path()}/review",
        headers=professor_headers(),
        json={
            "source_revision": edited["source_revision"],
            "practice_design_revision": edited["revision"],
        },
    )

    assert response.status_code == 502
    stored = client.get(_design_path(), headers=professor_headers()).json()
    assert stored["revision"] == edited["revision"]
    assert stored["quality_review"] is None


def test_provider_failures_do_not_persist_a_partial_design(tmp_path: Path) -> None:
    for index, (error, status_code) in enumerate(
        (
            (ProviderConfigurationError("Provider is unavailable."), 503),
            (ModelExecutionError("Provider request failed."), 502),
        )
    ):
        client = _client(tmp_path / str(index))
        client.app.state.practice_design_planner = _FailingPlanner(error)

        response = client.post(_proposal_path(), headers=professor_headers())

        assert response.status_code == status_code
        assert client.get(_design_path(), headers=professor_headers()).status_code == 404


def test_source_change_during_proposal_returns_conflict_without_persisting(tmp_path: Path) -> None:
    client = _client(tmp_path)
    source_path = (
        client.app.state.canvas_workspace.layout.course_uploads_dir(COURSE_ID) / "Lecture01.md"
    )
    client.app.state.practice_design_planner = _ChangingPlanner(source_path)

    response = client.post(_proposal_path(), headers=professor_headers())

    assert response.status_code == 409
    assert client.get(_design_path(), headers=professor_headers()).status_code == 404

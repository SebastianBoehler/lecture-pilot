from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import confirm_source_routing, professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.providers import ProviderConfigurationError


COURSE_ID = "practice-course"


class _Planner:
    calls = 0

    async def propose(self, *, source, source_revision, allowed_source_paths):
        from lecturepilot.course_practice_design_models import (
            PracticeDesignProposal,
            PracticeTarget,
        )

        self.calls += 1
        assert source.title == "Practice lecture"
        assert source_revision
        assert allowed_source_paths == ("Lecture01.md",)
        return PracticeDesignProposal(
            lecture_title="Practice lecture",
            objective="Calculate a posterior from stated evidence.",
            planning_context={
                "learner_level": None,
                "prerequisites": None,
                "time_budget_minutes": None,
                "allowed_aids": None,
                "assessment_conditions": None,
                "insufficiencies": [
                    {"field": field, "description": f"The source does not state {field}."}
                    for field in (
                        "learner_level",
                        "prerequisites",
                        "time_budget_minutes",
                        "allowed_aids",
                        "assessment_conditions",
                    )
                ],
            },
            targets=(
                PracticeTarget(
                    id="posterior",
                    title="Posterior",
                    outcome="Calculate a posterior from stated evidence.",
                    target_invariant="Apply Bayes rule to a stated prior and likelihood.",
                    baseline_task="Calculate the posterior for the stated prior and likelihood.",
                    independent_exit_task="Calculate a posterior for a different prior and likelihood.",
                    independent_exit_surface_change="Change only the stated probabilities.",
                    delayed_transfer_task="Choose and calculate a posterior for a changed diagnostic setting.",
                    delayed_transfer_surface_change=(
                        "Change the scenario and representation while preserving Bayes rule."
                    ),
                    evidence_criteria=({"id": "substitute", "description": "Uses stated values."},),
                    misconceptions=(),
                    hint_ladder=(),
                    review_after_days=7,
                    source_refs=("Lecture01.md",),
                ),
            ),
        )


def test_owner_can_propose_edit_and_approve_a_current_practice_design(tmp_path: Path) -> None:
    client = _client(tmp_path)
    planner = _Planner()
    client.app.state.practice_design_planner = planner

    proposed = client.post(_proposal_path(), headers=professor_headers())

    assert proposed.status_code == 200, proposed.json()
    design = proposed.json()
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
    approved = client.post(
        f"{_design_path()}/approve",
        headers=professor_headers(),
        json={
            "source_revision": updated.json()["source_revision"],
            "practice_design_revision": updated.json()["revision"],
        },
    )

    assert approved.status_code == 200
    assert approved.json()["approval"]["practice_design_revision"] == updated.json()["revision"]


def test_rejects_invalid_target_source_references(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.practice_design_planner = _Planner()
    design = client.post(_proposal_path(), headers=professor_headers()).json()
    target = design["targets"][0]
    target["source_refs"] = ["unrouted.md"]

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


class _FailingPlanner:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def propose(self, **_kwargs):
        raise self.error


class _ChangingPlanner(_Planner):
    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path

    async def propose(self, **kwargs):
        proposal = await super().propose(**kwargs)
        self.source_path.write_text(
            "# Changed source\n\nChanged posterior evidence.", encoding="utf-8"
        )
        return proposal


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "course"
    )
    client = TestClient(app)
    created = client.post(
        "/admin/course-workspaces",
        headers=professor_headers(),
        json={
            "course_title": "Practice Course",
            "target": "full-course",
            "replace_lectures": True,
            "lectures": [
                {
                    "number": "01",
                    "title": "Practice lecture",
                    "date": "2026-07-01",
                    "material_path": "Lecture01.md",
                }
            ],
        },
    )
    assert created.status_code == 200
    response = client.post(
        f"/admin/courses/{COURSE_ID}/materials",
        headers=professor_headers(),
        data={"path": "Lecture01.md"},
        files={
            "file": (
                "Lecture01.md",
                b"# Bayes rule\n\nBayes rule maps prior probabilities and likelihood evidence into posterior probabilities.",
            )
        },
    )
    assert response.status_code == 200
    confirm_source_routing(client, COURSE_ID)
    return client


def _design_path() -> str:
    return f"/admin/courses/{COURSE_ID}/lectures/lecture-01/practice-design"


def _proposal_path() -> str:
    return f"{_design_path()}/proposal"

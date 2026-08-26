from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import confirm_source_routing, professor_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_practice_design_review_models import (
    REVIEW_DIMENSIONS,
    PracticeDesignReviewResult,
)
from lecturepilot.model_client import ModelExecutionError


COURSE_ID = "practice-course"


class Planner:
    calls = 0

    def __init__(self, severity: str = "pass") -> None:
        self.severity = severity
        self.review_calls = 0

    async def propose(self, *, source, source_revision, allowed_source_paths):
        from lecturepilot.course_practice_design_models import (
            PracticeDesignProposal,
            PracticeTarget,
        )
        from lecturepilot.course_practice_design_planner import ReviewedPracticeDesignProposal

        self.calls += 1
        assert source.title == "Practice lecture"
        assert source_revision
        assert allowed_source_paths == ("Lecture01.md",)
        anchor = {
            "source_path": "Lecture01.md",
            "excerpt": (
                "Bayes rule maps prior probabilities and likelihood evidence into posterior "
                "probabilities."
            ),
        }
        proposal = PracticeDesignProposal(
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
                    outcome_anchor=anchor,
                    target_invariant="Apply Bayes rule to a stated prior and likelihood.",
                    target_invariant_anchor=anchor,
                    baseline_task="Calculate the posterior for the stated prior and likelihood.",
                    baseline_task_anchor=anchor,
                    independent_exit_task="Calculate a posterior for a different prior and likelihood.",
                    independent_exit_task_anchor=anchor,
                    independent_exit_surface_change="Change only the stated probabilities.",
                    delayed_transfer_task="Choose and calculate a posterior for a changed diagnostic setting.",
                    delayed_transfer_task_anchor=anchor,
                    delayed_transfer_surface_change=(
                        "Change the scenario and representation while preserving Bayes rule."
                    ),
                    evidence_criteria=(
                        {
                            "id": "substitute",
                            "description": "Uses stated values.",
                            "source_anchor": anchor,
                        },
                    ),
                    review_after_days=7,
                    source_refs=("Lecture01.md",),
                ),
            ),
        )
        return ReviewedPracticeDesignProposal(
            proposal=proposal,
            review=self._review_result(proposal.targets[0].id, anchor),
        )

    async def review(self, *, proposal, **_kwargs):
        self.review_calls += 1
        anchor = proposal.targets[0].outcome_anchor.model_dump(mode="python")
        return self._review_result(proposal.targets[0].id, anchor)

    def _review_result(self, target_id: str, anchor: dict) -> PracticeDesignReviewResult:
        severity = getattr(self, "severity", "pass")
        return PracticeDesignReviewResult(
            checks=[
                {
                    "dimension": dimension,
                    "severity": severity if dimension == REVIEW_DIMENSIONS[0] else "pass",
                    "summary": f"{dimension} review completed.",
                    "target_ids": [target_id],
                    "supporting_anchors": (
                        [anchor] if dimension == REVIEW_DIMENSIONS[0] and severity != "pass" else []
                    ),
                }
                for dimension in REVIEW_DIMENSIONS
            ]
        )


class FailingPlanner:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def propose(self, **_kwargs):
        raise self.error


class FailingReviewPlanner:
    async def review(self, **_kwargs):
        raise ModelExecutionError("Semantic critic unavailable.")


class ChangingPlanner(Planner):
    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path

    async def propose(self, **kwargs):
        proposal = await super().propose(**kwargs)
        self.source_path.write_text(
            "# Changed source\n\nChanged posterior evidence.", encoding="utf-8"
        )
        return proposal


def client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "course"
    )
    test_client = TestClient(app)
    created = test_client.post(
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
    response = test_client.post(
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
    confirm_source_routing(test_client, COURSE_ID)
    return test_client


def design_path() -> str:
    return f"/admin/courses/{COURSE_ID}/lectures/lecture-01/practice-design"


def proposal_path() -> str:
    return f"{design_path()}/proposal"

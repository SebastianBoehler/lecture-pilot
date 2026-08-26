import pytest
from pydantic import ValidationError

from lecturepilot.course_practice_design_models import PracticeDesignProposal
from practice_design_test_helpers import proposal, target


def _expanded_proposal_payload() -> dict:
    payload = proposal().model_dump(mode="json")
    payload["targets"][0].update(
        {
            "target_invariant": "Derive a conclusion by connecting the evidence to the claim.",
            "independent_exit_surface_change": (
                "Change the evidence values while preserving the required derivation."
            ),
            "delayed_transfer_surface_change": (
                "Change the scenario and representation without adding new knowledge."
            ),
        }
    )
    return payload


def test_contract_round_trips_planning_context_and_controlled_task_variants() -> None:
    proposal_payload = _expanded_proposal_payload()
    proposal_payload["planning_context"] = {
        "learner_level": "Undergraduate learners in this lecture.",
        "prerequisites": ["Interpret the supplied evidence."],
        "time_budget_minutes": 30,
        "allowed_aids": ["Course notes"],
        "assessment_conditions": "Complete each assessment individually.",
        "insufficiencies": [],
    }

    parsed = PracticeDesignProposal.model_validate(proposal_payload)

    assert parsed.planning_context.time_budget_minutes == 30
    assert parsed.targets[0].target_invariant.startswith("Derive a conclusion")
    assert parsed.targets[0].independent_exit_surface_change.startswith("Change the evidence")
    assert parsed.targets[0].delayed_transfer_surface_change.startswith("Change the scenario")


def test_planning_context_requires_one_explicit_insufficiency_for_each_missing_field() -> None:
    proposal_payload = _expanded_proposal_payload()
    proposal_payload["planning_context"] = {
        "learner_level": None,
        "prerequisites": ["Interpret the supplied evidence."],
        "time_budget_minutes": None,
        "allowed_aids": None,
        "assessment_conditions": "Complete each assessment individually.",
        "insufficiencies": [
            {
                "field": "learner_level",
                "description": "The supplied source does not state the learner level.",
            },
            {
                "field": "time_budget_minutes",
                "description": "The supplied source does not state a time budget.",
            },
            {
                "field": "allowed_aids",
                "description": "The supplied source does not state which aids are allowed.",
            },
        ],
    }

    parsed = PracticeDesignProposal.model_validate(proposal_payload)

    assert tuple(item.field for item in parsed.planning_context.insufficiencies) == (
        "learner_level",
        "time_budget_minutes",
        "allowed_aids",
    )
    proposal_payload["planning_context"]["insufficiencies"] = []
    with pytest.raises(ValidationError, match="explicit insufficiency"):
        PracticeDesignProposal.model_validate(proposal_payload)


def test_target_requires_at_least_one_required_evidence_criterion() -> None:
    with pytest.raises(ValidationError, match="required evidence criterion"):
        target(
            evidence_criteria=[
                {
                    "id": "optional-note",
                    "description": "Records an optional observation.",
                    "required": False,
                }
            ]
        )

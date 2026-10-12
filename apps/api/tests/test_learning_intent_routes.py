import json

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from auth_helpers import professor_headers
from lecturepilot.course_practice_design_planner import PracticeDesignPlanner
from practice_design_route_test_helpers import client, design_path
from practice_design_test_helpers import proposal
from test_practice_design_semantic_review import _Registry


def goal_client(tmp_path, *, goal_count=1, findings=((),), finding_ids=None):
    """`findings` lists the goal IDs the support reviewer flags on each review call."""
    api = client(tmp_path)
    draft = proposal()
    goal = {
        key: getattr(draft.targets[0], key)
        for key in ("id", "title", "outcome", "target_invariant")
    }
    goal.update(outcome_anchor="e0", target_invariant_anchor="e0")
    wire = {
        "lecture_title": "Practice lecture",
        "objective": "A broad module objective promising more than the goals.",
        "planning_context": draft.planning_context.model_dump(mode="json"),
        "goals": [{**goal, "id": f"goal-{index}"} for index in range(goal_count)],
    }
    calls = []
    reviewed = 0
    repairing = False

    def respond(messages, info):
        nonlocal reviewed, repairing
        calls.append(info.model_request_parameters)
        properties = info.model_request_parameters.output_object.json_schema["properties"]
        if "findings" in properties:
            flagged = findings[min(reviewed, len(findings) - 1)]
            reviewed += 1
            repairing = bool(finding_ids or flagged)
            return ModelResponse(
                parts=[
                    TextPart(
                        json.dumps(
                            {
                                "findings": [
                                    {"goal_id": goal_id, "reason": "The source only names this."}
                                    for goal_id in (finding_ids or flagged)
                                ],
                                "evidence_ids": ["e0"],
                            }
                        )
                    )
                ]
            )
        assert ("current_proposal" in messages[-1].parts[0].content) == repairing
        repairing = False
        return ModelResponse(parts=[TextPart(json.dumps(wire))])

    api.app.state.practice_design_planner = PracticeDesignPlanner(
        provider_registry=_Registry(), model=FunctionModel(respond)
    )
    return api, calls


def findings_for(api):
    return api.get(design_path() + "/intent/findings", headers=professor_headers()).json()


def test_objective_is_derived_from_the_proposed_goals(tmp_path):
    api, calls = goal_client(tmp_path, goal_count=2)
    response = api.post(design_path() + "/intent/proposal", headers=professor_headers())
    assert response.status_code == 200, response.text
    intent = response.json()["learning_intent"]
    outcomes = [goal["outcome"] for goal in intent["goals"]]
    assert intent["objective"] == f"1) {outcomes[0]}\n2) {outcomes[1]}"
    assert len(calls) == 2
    assert findings_for(api) == []


def test_flagged_goals_get_one_repair_then_stay_as_professor_findings(tmp_path):
    api, calls = goal_client(tmp_path, goal_count=2, findings=(("goal-0",),))
    response = api.post(design_path() + "/intent/proposal", headers=professor_headers())
    assert response.status_code == 200, response.text
    assert [goal["id"] for goal in response.json()["learning_intent"]["goals"]] == [
        "goal-0",
        "goal-1",
    ]
    assert len(calls) == 4
    assert findings_for(api) == [{"goal_id": "goal-0", "reason": "The source only names this."}]


def test_repaired_goals_without_findings_are_clean(tmp_path):
    api, calls = goal_client(tmp_path, findings=(("goal-0",), ()))
    assert api.post(design_path() + "/intent/proposal", headers=professor_headers()).is_success
    assert len(calls) == 4
    assert findings_for(api) == []


def test_support_reviewer_must_name_existing_goals(tmp_path):
    api, calls = goal_client(tmp_path, finding_ids=("goal-x",))
    response = api.post(design_path() + "/intent/proposal", headers=professor_headers())
    assert response.status_code == 502, response.text
    assert "could not be grounded" in response.json()["detail"]
    assert api.get(design_path(), headers=professor_headers()).status_code == 404


def test_findings_never_block_approval_and_edits_clear_them(tmp_path):
    api, calls = goal_client(tmp_path, findings=(("goal-0",),))
    design = api.post(design_path() + "/intent/proposal", headers=professor_headers()).json()
    count = len(calls)
    approval = api.post(
        design_path() + "/intent/approve",
        headers=professor_headers(),
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
        },
    )
    assert approval.status_code == 200, approval.text
    assert len(calls) == count
    edited = approval.json()
    goal = {**edited["learning_intent"]["goals"][0], "outcome": "Explain the cited source claim."}
    changed = api.put(
        design_path() + "/intent",
        headers=professor_headers(),
        json={
            "source_revision": edited["source_revision"],
            "practice_design_revision": edited["revision"],
            "lecture_title": edited["lecture_title"],
            "objective": "Ignored: the backend derives it.",
            "planning_context": edited["planning_context"],
            "goals": [goal],
        },
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["objective"] == "1) Explain the cited source claim."
    assert findings_for(api) == []


def test_source_to_goals_approval_does_not_generate_or_approve_tasks(tmp_path):
    api, calls = goal_client(tmp_path)
    response = api.post(design_path() + "/intent/proposal", headers=professor_headers())
    assert response.status_code == 200, response.text
    design = response.json()
    assert design["targets"] == []
    assert design["quality_review"] is None
    assert len(calls) == 2
    assert calls[0].output_mode == "native"
    assert "baseline_task" not in json.dumps(calls[0].output_object.json_schema)
    assert (
        api.get(design_path() + "/readiness", headers=professor_headers()).json()[
            "ready_for_generation"
        ]
        is False
    )
    approval = api.post(
        design_path() + "/intent/approve",
        headers=professor_headers(),
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
        },
    )
    assert approval.status_code == 200, approval.text
    assert approval.json()["approval"] is None
    assert approval.json()["learning_intent"]["approval"]
    assert (
        api.get(design_path() + "/readiness", headers=professor_headers()).json()[
            "ready_for_generation"
        ]
        is True
    )
    assert len(calls) == 2
    assert api.post(
        design_path() + "/intent/approve",
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
        },
    ).status_code in {401, 403}


def test_goal_edit_requires_new_approval_and_rejects_stale_submission(tmp_path):
    api, _ = goal_client(tmp_path)
    design = api.post(design_path() + "/intent/proposal", headers=professor_headers()).json()
    design = api.post(
        design_path() + "/intent/approve",
        headers=professor_headers(),
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
        },
    ).json()
    update = {
        "source_revision": design["source_revision"],
        "practice_design_revision": design["revision"],
        "lecture_title": design["lecture_title"],
        "objective": design["objective"],
        "planning_context": design["planning_context"],
        "goals": [
            {**design["learning_intent"]["goals"][0], "title": "Justify a supported conclusion"}
        ],
    }
    changed = api.put(design_path() + "/intent", headers=professor_headers(), json=update)
    assert changed.status_code == 200, changed.text
    assert changed.json()["learning_intent"]["approval"] is None
    assert changed.json()["revision"] != design["revision"]
    assert (
        api.put(design_path() + "/intent", headers=professor_headers(), json=update).status_code
        == 409
    )


def test_professor_can_rename_and_remove_goals_with_fresh_approval_required(tmp_path):
    api, _ = goal_client(tmp_path, goal_count=2)
    design = api.post(design_path() + "/intent/proposal", headers=professor_headers()).json()
    design = api.post(
        design_path() + "/intent/approve",
        headers=professor_headers(),
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
        },
    ).json()
    update = {
        "source_revision": design["source_revision"],
        "practice_design_revision": design["revision"],
        "lecture_title": design["lecture_title"],
        "objective": design["objective"],
        "planning_context": design["planning_context"],
        "goals": [{**design["learning_intent"]["goals"][0], "title": "Professor revised goal"}],
    }
    changed = api.put(design_path() + "/intent", headers=professor_headers(), json=update)
    assert changed.status_code == 200, changed.text
    saved = changed.json()
    assert len(saved["learning_intent"]["goals"]) == 1
    assert saved["learning_intent"]["goals"][0]["title"] == "Professor revised goal"
    assert saved["learning_intent"]["approval"] is None
    assert not api.get(design_path() + "/readiness", headers=professor_headers()).json()[
        "ready_for_generation"
    ]


def test_refresh_regenerates_unapproved_goals_through_the_goal_proposal(tmp_path):
    api, calls = goal_client(tmp_path)
    first = api.post(design_path() + "/intent/proposal", headers=professor_headers())
    assert first.status_code == 200, first.text
    assert len(calls) == 2
    cached = api.post(design_path() + "/intent/proposal", headers=professor_headers())
    assert cached.json() == first.json()
    assert len(calls) == 2
    refreshed = api.post(
        design_path() + "/intent/proposal?refresh=true", headers=professor_headers()
    )
    assert refreshed.status_code == 200, refreshed.text
    # One goal proposal plus one advisory support review: no full-plan model loop.
    assert len(calls) == 4
    assert all("baseline_task" not in json.dumps(call.output_object.json_schema) for call in calls)
    assert refreshed.json()["targets"] == []
    assert refreshed.json()["learning_intent"]["approval"] is None


def test_refresh_keeps_approved_goals(tmp_path):
    api, calls = goal_client(tmp_path)
    design = api.post(design_path() + "/intent/proposal", headers=professor_headers()).json()
    approved = api.post(
        design_path() + "/intent/approve",
        headers=professor_headers(),
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
        },
    ).json()
    response = api.post(
        design_path() + "/intent/proposal?refresh=true", headers=professor_headers()
    )
    assert response.status_code == 409, response.text
    assert len(calls) == 2
    assert api.get(design_path(), headers=professor_headers()).json() == approved

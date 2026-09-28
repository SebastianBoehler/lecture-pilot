import json

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from auth_helpers import professor_headers
from lecturepilot.course_practice_design_planner import PracticeDesignPlanner
from practice_design_route_test_helpers import client, design_path
from practice_design_test_helpers import proposal
from test_practice_design_semantic_review import _Registry


def goal_client(tmp_path, *, goal_count=1, scope_reviews=(True,)):
    api = client(tmp_path)
    draft = proposal()
    goal = {
        key: getattr(draft.targets[0], key)
        for key in (
            "id",
            "title",
            "outcome",
            "target_invariant",
        )
    }
    goal.update(outcome_anchor="e0", target_invariant_anchor="e0")
    wire = {
        "lecture_title": "Practice lecture",
        "objective": draft.objective,
        "planning_context": draft.planning_context.model_dump(mode="json"),
        "goals": [{**goal, "id": f"goal-{index}"} for index in range(goal_count)],
    }
    calls = []
    reviewed = 0

    def respond(messages, info):
        nonlocal reviewed
        calls.append(info.model_request_parameters)
        if "coherent" in info.model_request_parameters.output_object.json_schema["properties"]:
            coherent = scope_reviews[min(reviewed, len(scope_reviews) - 1)]
            reviewed += 1
            return ModelResponse(
                parts=[
                    TextPart(
                        json.dumps(
                            {
                                "coherent": coherent,
                                "reason": "An objective capability needs a goal or a narrower objective.",
                                "evidence_ids": ["e0"],
                            }
                        )
                    )
                ]
            )
        if reviewed:
            assert "Scope review" in messages[-1].parts[0].content
        return ModelResponse(parts=[TextPart(json.dumps(wire))])

    api.app.state.practice_design_planner = PracticeDesignPlanner(
        provider_registry=_Registry(),
        model=FunctionModel(respond),
    )
    return api, calls


def test_goal_scope_is_repaired_before_professor_review(tmp_path):
    api, calls = goal_client(tmp_path, scope_reviews=(False, True))
    response = api.post(design_path() + "/intent/proposal", headers=professor_headers())
    assert response.status_code == 200, response.text
    assert len(calls) == 4
    assert response.json()["learning_intent"]["approval"] is None
    assert response.json()["targets"] == []


def test_inconsistent_goal_scope_cannot_be_saved_for_approval(tmp_path):
    api, calls = goal_client(tmp_path, scope_reviews=(False,))
    response = api.post(design_path() + "/intent/proposal", headers=professor_headers())
    assert response.status_code == 502, response.text
    assert "inconsistent after repair" in response.json()["detail"]
    assert len(calls) == 6
    assert api.get(design_path(), headers=professor_headers()).status_code == 404


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
        "objective": "Justify a source-supported conclusion.",
        "planning_context": design["planning_context"],
        "goals": design["learning_intent"]["goals"],
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

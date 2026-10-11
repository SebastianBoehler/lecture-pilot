import json

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from auth_helpers import professor_headers
from lecturepilot.course_practice_design_planner import PracticeDesignPlanner
from practice_design_route_test_helpers import design_path
from test_learning_intent_routes import goal_client
from test_practice_design_semantic_review import _Registry


def edited_design(api):
    design = api.post(design_path() + "/intent/proposal", headers=professor_headers()).json()
    return api.put(
        design_path() + "/intent",
        headers=professor_headers(),
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
            "lecture_title": design["lecture_title"],
            "objective": "Explain the modified capability.",
            "planning_context": design["planning_context"],
            "goals": design["learning_intent"]["goals"],
        },
    ).json()


def approve(api, design):
    return api.post(
        design_path() + "/intent/approve",
        headers=professor_headers(),
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
        },
    )


def review_model(api, *, coherent, before_response=lambda: None):
    calls = []

    def respond(messages, info):
        calls.append(info)
        before_response()
        return ModelResponse(
            parts=[
                TextPart(
                    json.dumps(
                        {
                            "coherent": coherent,
                            "unsupported_goal_ids": [] if coherent else ["goal-0"],
                            "reason": "The modified capability lacks source support.",
                            "evidence_ids": ["e0"],
                        }
                    )
                )
            ]
        )

    api.app.state.practice_design_planner = PracticeDesignPlanner(
        provider_registry=_Registry(),
        model=FunctionModel(respond),
    )
    return calls


def test_unsupported_edited_intent_is_not_approved(tmp_path):
    api, _ = goal_client(tmp_path)
    design = edited_design(api)
    calls = review_model(api, coherent=False)
    response = approve(api, design)
    assert response.status_code == 409, response.text
    assert "source support" in response.json()["detail"]
    assert len(calls) == 1
    saved = api.get(design_path(), headers=professor_headers()).json()
    assert saved["revision"] == design["revision"]
    assert saved["learning_intent"]["approval"] is None


def test_supported_edited_intent_is_checked_once_and_cached(tmp_path):
    api, _ = goal_client(tmp_path)
    design = edited_design(api)
    calls = review_model(api, coherent=True)
    assert approve(api, design).status_code == 200
    assert approve(api, design).status_code == 200
    assert len(calls) == 1


def test_intent_changed_during_review_is_not_approved(tmp_path):
    api, _ = goal_client(tmp_path)
    design = edited_design(api)

    def change():
        api.put(
            design_path() + "/intent",
            headers=professor_headers(),
            json={
                "source_revision": design["source_revision"],
                "practice_design_revision": design["revision"],
                "lecture_title": design["lecture_title"],
                "objective": "A newer objective.",
                "planning_context": design["planning_context"],
                "goals": design["learning_intent"]["goals"],
            },
        )

    calls = review_model(api, coherent=True, before_response=change)
    response = approve(api, design)
    assert response.status_code == 409
    assert len(calls) == 1
    assert (
        api.get(design_path(), headers=professor_headers()).json()["learning_intent"]["approval"]
        is None
    )


def test_failed_scope_review_does_not_record_approval(tmp_path, monkeypatch):
    from lecturepilot.model_client import ModelExecutionError

    api, _ = goal_client(tmp_path)
    design = edited_design(api)

    async def fail(*args, **kwargs):
        raise ModelExecutionError("Scope reviewer unavailable.")

    monkeypatch.setattr("lecturepilot.course_learning_intent_routes.require_approvable_scope", fail)
    response = approve(api, design)
    assert response.status_code == 502
    assert (
        api.get(design_path(), headers=professor_headers()).json()["learning_intent"]["approval"]
        is None
    )

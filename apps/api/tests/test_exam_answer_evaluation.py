import json
import sys
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.exam_answer_evaluation import (
    LiteLLMOpenAnswerEvaluationClient,
    OpenAnswerEvaluation,
    OpenAnswerEvaluationInput,
    OpenAnswerEvaluator,
)
from lecturepilot.models import ProviderSettings
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry
from fastapi.testclient import TestClient


def _item(question_id: str = "lecture-04:risk:open") -> OpenAnswerEvaluationInput:
    return OpenAnswerEvaluationInput(
        question_id=question_id,
        prompt="Explain expected risk.",
        answer="Expected risk combines losses and posterior probabilities.",
        rubric=["Compare posterior-weighted losses.", "Name one failure mode."],
    )


async def test_evaluator_returns_rubric_grounded_score_and_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "evaluations": [
                                    {
                                        "question_id": "lecture-04:risk:open",
                                        "score": 0.75,
                                        "feedback": "Good explanation; add one concrete failure mode.",
                                    }
                                ]
                            }
                        )
                    )
                )
            ]
        )

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))
    evaluator = OpenAnswerEvaluator(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=LiteLLMOpenAnswerEvaluationClient(),
    )

    evaluations = await evaluator.evaluate(items=[_item()])

    assert evaluations[0].score == 0.75
    assert evaluations[0].feedback
    assert calls[0]["temperature"] == 0.1
    assert calls[0]["response_format"]["json_schema"]["strict"] is True
    assert "Expected risk combines" in calls[0]["messages"][1]["content"]


@pytest.mark.parametrize(
    "payload, error",
    [
        (
            {"evaluations": []},
            "must match submitted open-question ids",
        ),
        (
            {
                "evaluations": [
                    {"question_id": "lecture-04:risk:open", "score": 0.75, "feedback": "Useful."},
                    {"question_id": "lecture-04:risk:open", "score": 0.5, "feedback": "Repeat."},
                ]
            },
            "must match submitted open-question ids",
        ),
        (
            {"evaluations": [{"question_id": "invented", "score": 0.75, "feedback": "Useful."}]},
            "must match submitted open-question ids",
        ),
    ],
)
async def test_evaluator_rejects_missing_duplicated_or_invented_ids(
    payload: dict,
    error: str,
) -> None:
    evaluator = OpenAnswerEvaluator(model_client=_StaticEvaluationClient(payload))

    with pytest.raises(ProviderConfigurationError, match=error):
        await evaluator.evaluate(
            settings=ProviderSettings(
                provider="gemini",
                model="gemini/test-model",
                api_key_env="GEMINI_API_KEY",
                capabilities=set(),
            ),
            items=[_item()],
        )


@pytest.mark.parametrize("score", [-0.01, 1.01])
async def test_evaluator_rejects_scores_outside_zero_to_one(score: float) -> None:
    evaluator = OpenAnswerEvaluator(
        model_client=_StaticEvaluationClient(
            {
                "evaluations": [
                    {
                        "question_id": "lecture-04:risk:open",
                        "score": score,
                        "feedback": "Useful feedback.",
                    }
                ]
            }
        )
    )

    with pytest.raises(ValidationError):
        await evaluator.evaluate(
            settings=ProviderSettings(
                provider="gemini",
                model="gemini/test-model",
                api_key_env="GEMINI_API_KEY",
                capabilities=set(),
            ),
            items=[_item()],
        )


class _StaticEvaluationClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def complete_evaluations(
        self, *, settings: ProviderSettings, items: list[object]
    ) -> dict:
        return self.payload


def test_evaluation_failure_returns_retryable_response_without_persisting(tmp_path) -> None:
    client = create_app()
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    client.state.canvas_workspace = workspace
    client.state.open_answer_evaluator = _FailingEvaluator()
    browser = TestClient(client)
    browser.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Demo ML Course",
            "target": "single-lecture",
            "lecture_number": "03",
            "lecture_title": "Bayesian Decision Theory",
        },
        headers=professor_headers(),
    )
    workspace.write_course_canvas(_route_document())

    response = browser.post(
        "/courses/demo-ml-course/exam-readiness/attempts",
        headers=student_headers("student-a"),
        json={
            "answers": [
                {"question_id": "lecture-03:quiz", "selected_index": 1},
                {"question_id": "lecture-03:section:open", "text": "Expected risk uses losses."},
            ]
        },
    )

    assert response.status_code == 503
    assert not (
        workspace.layout.user_course_root("student-a", "demo-ml-course") / "progress.json"
    ).exists()


class _FailingEvaluator:
    async def evaluate(self, **_kwargs) -> list[OpenAnswerEvaluation]:
        raise ProviderConfigurationError("Evaluation provider is unavailable.")


def _route_document() -> CanvasDocument:
    return CanvasDocument(
        id="demo-ml-course-lecture-03",
        course_id="demo-ml-course",
        lecture_id="lecture-03",
        title="Bayesian Decision Theory",
        source_kind="generated",
        source_ref="lecture-03.tex",
        workspace_path="course/canvas/index.md",
        sections=[
            CanvasSection(
                id="section",
                title="Expected risk",
                source_ref="lecture-03.tex",
                blocks=[
                    CanvasBlock(
                        id="quiz",
                        type="quiz",
                        text="Which quantity should be minimized?",
                        items=["Posterior", "Expected risk"],
                        answer_index=1,
                    ),
                    CanvasBlock(
                        id="paragraph",
                        type="paragraph",
                        text="Expected risk combines posterior probabilities and losses.",
                    ),
                ],
            )
        ],
    )

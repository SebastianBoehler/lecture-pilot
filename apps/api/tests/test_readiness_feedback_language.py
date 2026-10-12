import json

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelResponse, SystemPromptPart, TextPart
from pydantic_ai.models.function import FunctionModel

from auth_helpers import professor_headers, student_headers
from canvas_workspace_fixtures import publish_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas.canvas_workspace import CanvasWorkspace
from lecturepilot.exams.exam_answer_evaluation import (
    NativeOpenAnswerEvaluationClient,
    OpenAnswerEvaluator,
)
from lecturepilot.llm.providers import ProviderRegistry
from test_exam_answer_evaluation import _FailingEvaluator, _item, _route_document


async def test_feedback_language_is_stated_not_inferred(monkeypatch: pytest.MonkeyPatch) -> None:
    systems: list[str] = []

    def respond(messages, info):
        for message in messages:
            systems.append(getattr(message, "instructions", None) or "")
            systems.extend(
                part.content for part in message.parts if isinstance(part, SystemPromptPart)
            )
        payload = {
            "evaluations": [{"question_id": _item().question_id, "score": 1.0, "feedback": "Gut."}]
        }
        return ModelResponse(parts=[TextPart(json.dumps(payload))])

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    evaluator = OpenAnswerEvaluator(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=NativeOpenAnswerEvaluationClient(model=FunctionModel(respond)),
    )
    await evaluator.evaluate(items=[_item().model_copy(update={"feedback_language": "de"})])

    assert "Write all feedback in German" in " ".join(systems)
    assert "language of the learner answer" not in " ".join(systems)


@pytest.mark.parametrize(("locale", "expected"), [("de", "de"), (None, "en")])
def test_readiness_feedback_follows_the_learner_locale(tmp_path, locale, expected) -> None:
    app = create_app()
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    app.state.canvas_workspace = workspace
    app.state.open_answer_evaluator = _FailingEvaluator()
    browser = TestClient(app)
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
    publish_course_canvas(workspace, _route_document())
    answers = [
        {"question_id": "lecture-03:quiz", "selected_index": 1},
        {"question_id": "lecture-03:section:open", "text": "Expected risk uses losses."},
        {"question_id": "lecture-03:practice-practice-target:open", "text": "Losses."},
    ]

    browser.post(
        "/courses/demo-ml-course/exam-readiness/attempts",
        headers=student_headers("student-a"),
        json={"answers": answers, **({"feedback_locale": locale} if locale else {})},
    )

    assert {item.feedback_language for item in app.state.open_answer_evaluator.items} == {expected}

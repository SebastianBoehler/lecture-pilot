from __future__ import annotations

from copy import deepcopy

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.practice_exam_planner import (
    PracticeExamPlanner,
    PracticeExamPlanningError,
)
from lecturepilot.practice_exam_prompt import (
    MAX_COURSE_EVIDENCE_CHARS,
    authoritative_canvas_evidence,
)
from lecturepilot.practice_exam_schema import practice_exam_response_format


@pytest.mark.asyncio
async def test_planner_generates_valid_grounded_exam() -> None:
    client = _ModelClient([_payload()])
    planner = PracticeExamPlanner(provider_registry=_Registry(), model_client=client)

    exam = await planner.plan(
        course_id="martius-ml",
        course_title="Machine Learning",
        language="en",
        duration_minutes=90,
        question_count=20,
        documents=[_document()],
        ppi_sources={"ppi-42": ["Old exams often use short transfer scenarios."]},
    )

    assert len(exam.questions) == 20
    assert exam.ppi_source_ids == ["ppi-42"]
    assert exam.source_ids == ["lecture-01:risk:definition"]
    assert len(exam.source_revision) == 64
    assert client.calls == 1
    assert "non-authoritative pattern evidence" in client.messages[0][1]["content"]


@pytest.mark.asyncio
async def test_planner_propagates_provider_failure() -> None:
    planner = PracticeExamPlanner(
        provider_registry=_Registry(), model_client=_ModelClient([ModelExecutionError("down")])
    )

    with pytest.raises(ModelExecutionError, match="down"):
        await planner.plan(**_plan_args())


@pytest.mark.asyncio
async def test_planner_rejects_malformed_payload() -> None:
    payload = _payload()
    del payload["questions"][0]["prompt"]
    planner = PracticeExamPlanner(
        provider_registry=_Registry(), model_client=_ModelClient([payload, payload])
    )

    with pytest.raises(PracticeExamPlanningError, match="valid structured exam"):
        await planner.plan(**_plan_args())


@pytest.mark.asyncio
async def test_planner_repairs_duplicate_question_once() -> None:
    duplicate = _payload()
    duplicate["questions"][1]["prompt"] = duplicate["questions"][0]["prompt"]
    client = _ModelClient([duplicate, _payload()])
    planner = PracticeExamPlanner(provider_registry=_Registry(), model_client=client)

    exam = await planner.plan(**_plan_args())

    assert len(exam.questions) == 20
    assert client.calls == 2
    assert "unique prompts" in client.messages[1][0]["content"]


@pytest.mark.asyncio
async def test_planner_fails_after_bounded_repair() -> None:
    duplicate = _payload()
    duplicate["questions"][1]["prompt"] = duplicate["questions"][0]["prompt"]
    planner = PracticeExamPlanner(
        provider_registry=_Registry(), model_client=_ModelClient([duplicate, duplicate])
    )

    with pytest.raises(PracticeExamPlanningError, match="unique prompts"):
        await planner.plan(**_plan_args())


@pytest.mark.asyncio
async def test_planner_requires_unlocked_course_evidence() -> None:
    client = _ModelClient([_payload()])
    planner = PracticeExamPlanner(provider_registry=_Registry(), model_client=client)

    with pytest.raises(PracticeExamPlanningError, match="unlocked course content"):
        await planner.plan(**{**_plan_args(), "documents": []})
    assert client.calls == 0


def test_provider_schema_is_strict_and_requires_authoring_fields() -> None:
    response_format = practice_exam_response_format(
        question_count=25,
        authoritative_source_ids={"lecture-02:tokens:definition", "lecture-01:nlp:definition"},
        selected_ppi_source_ids=set(),
    )
    schema = response_format["json_schema"]["schema"]
    question_array = schema["properties"]["questions"]
    question = question_array["items"]

    assert response_format["json_schema"]["strict"] is True
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"title", "instructions", "questions"}
    assert question_array["minItems"] == question_array["maxItems"] == 25
    assert question["properties"]["source_ids"]["items"]["enum"] == [
        "lecture-01:nlp:definition",
        "lecture-02:tokens:definition",
    ]
    assert question["properties"]["ppi_pattern_ids"]["maxItems"] == 0


def test_authoritative_ids_include_only_evidence_visible_to_the_model() -> None:
    document = _document()
    document.sections[0].blocks = [
        CanvasBlock(id=f"block-{index}", type="paragraph", text=str(index) * 20_000)
        for index in range(4)
    ]

    evidence, source_ids = authoritative_canvas_evidence([document])

    assert len(evidence) <= MAX_COURSE_EVIDENCE_CHARS
    assert source_ids
    assert len(source_ids) < 4
    assert all(source_id in evidence for source_id in source_ids)


def _plan_args() -> dict:
    return {
        "course_id": "martius-ml",
        "course_title": "Machine Learning",
        "language": "en",
        "duration_minutes": 90,
        "question_count": 20,
        "documents": [_document()],
        "ppi_sources": {},
    }


def _document() -> CanvasDocument:
    return CanvasDocument(
        id="canvas-1",
        course_id="martius-ml",
        lecture_id="lecture-01",
        title="Risk minimization",
        source_kind="markdown",
        source_ref="lecture-01.md",
        workspace_path="canvas/lectures/lecture-01/index.md",
        sections=[
            CanvasSection(
                id="risk",
                title="Empirical risk",
                blocks=[
                    CanvasBlock(
                        id="definition",
                        type="paragraph",
                        text="Empirical risk averages loss over the observed training sample.",
                    )
                ],
            )
        ],
    )


def _payload() -> dict:
    questions = []
    for index in range(1, 21):
        questions.append(
            {
                "id": f"q-{index:02d}",
                "kind": "multiple_choice" if index % 2 else "open_ended",
                "prompt": f"Question {index}: apply empirical risk in scenario {index}?",
                "points": 2,
                "difficulty": "standard",
                "options": ["A", "B", "C", "D"] if index % 2 else [],
                "answer_index": 1 if index % 2 else None,
                "rubric": [] if index % 2 else ["Defines risk", "Applies the definition"],
                "source_ids": ["lecture-01:risk:definition"],
                "ppi_pattern_ids": [],
            }
        )
    return {
        "title": "Machine Learning practice exam",
        "instructions": ["Answer every question."],
        "questions": questions,
    }


class _Registry:
    def require_ready(self, required: list[ProviderCapability]) -> ProviderSettings:
        assert required == [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        return ProviderSettings(
            provider="gemini",
            model="gemini/test-model",
            api_key_env="GEMINI_API_KEY",
            capabilities=set(required),
        )


class _ModelClient:
    def __init__(self, responses: list[dict | Exception]) -> None:
        self.responses = responses
        self.calls = 0
        self.messages: list[list[dict[str, str]]] = []
        self.response_formats: list[dict] = []

    async def complete_exam(self, *, settings, messages, response_format):
        self.messages.append(deepcopy(messages))
        self.response_formats.append(deepcopy(response_format))
        response = self.responses[self.calls]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        return deepcopy(response)

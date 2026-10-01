from __future__ import annotations

import pytest

from practice_exam_planner_fixtures import (
    _ModelClient,
    _Registry,
    _document,
    _payload,
    _plan_args,
    _review_payload,
)

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.practice_exam_planner import (
    PracticeExamPlanner,
    PracticeExamPlanningError,
    _exam_output_token_budget,
)
from lecturepilot.practice_exam_prompt import (
    MAX_COURSE_EVIDENCE_CHARS,
    authoritative_canvas_evidence,
    practice_exam_messages,
)
from lecturepilot.practice_exam_schema import practice_exam_response_format


@pytest.mark.asyncio
async def test_planner_generates_valid_grounded_exam() -> None:
    client = _ModelClient([_payload(), _review_payload()])
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
    assert client.calls == 2
    assert "non-authoritative pattern evidence" in client.messages[0][1]["content"]
    assert "independent correctness reviewer" in client.messages[1][0]["content"]


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
    client = _ModelClient([duplicate, _payload(), _review_payload()])
    planner = PracticeExamPlanner(provider_registry=_Registry(), model_client=client)

    exam = await planner.plan(**_plan_args())

    assert len(exam.questions) == 20
    assert client.calls == 3
    assert "unique prompts" in client.messages[1][0]["content"]


@pytest.mark.asyncio
async def test_planner_regenerates_after_independent_answer_review_failure() -> None:
    failed_review = _review_payload()
    failed_review["reviews"][0] = {
        "question_id": "q-01",
        "verdict": "fail",
        "issue": "The keyed option contradicts the cited definition.",
        "source_ids": ["lecture-01:risk:definition"],
    }
    client = _ModelClient([_payload(), failed_review, _payload(), _review_payload()])
    planner = PracticeExamPlanner(provider_registry=_Registry(), model_client=client)

    exam = await planner.plan(**_plan_args())

    assert len(exam.questions) == 20
    assert client.calls == 4
    assert "keyed option contradicts" in client.messages[2][0]["content"]


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
    assert _exam_output_token_budget(25) == 20_000
    assert _exam_output_token_budget(50) == 30_000


def test_generation_prompt_defines_the_supported_exam_markup_contract() -> None:
    system = practice_exam_messages(
        course_title="Machine Learning",
        language="en",
        duration_minutes=90,
        question_count=20,
        course_evidence="[lecture-01:risk:definition] Empirical risk.",
        ppi_evidence="",
    )[0]["content"]

    assert "backticks" in system
    assert "$...$" in system
    assert "raw HTML" in system
    assert "LaTeX document commands" in system


def test_authoritative_ids_include_only_evidence_visible_to_the_model() -> None:
    document = _document()
    document.sections[0].blocks = [
        CanvasBlock(id=f"block-{index}", type="paragraph", text=str(index) * 20_000)
        for index in range(4)
    ]

    evidence, source_ids = authoritative_canvas_evidence([document])

    assert len(evidence) <= MAX_COURSE_EVIDENCE_CHARS
    assert source_ids
    assert len(source_ids) == 4
    assert all(source_id in evidence for source_id in source_ids)


def test_authoritative_evidence_excludes_sections_marked_ineligible() -> None:
    document = _document()
    document.sections.append(
        CanvasSection(
            id="exam-logistics",
            title="Exam logistics",
            practice_exam_eligible=False,
            blocks=[CanvasBlock(id="date", type="paragraph", text="The exam is Monday.")],
        )
    )

    evidence, source_ids = authoritative_canvas_evidence([document])

    assert "The exam is Monday" not in evidence
    assert "lecture-01:exam-logistics:date" not in source_ids


def test_planner_uses_practice_exam_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_MODEL", "openai/gpt-5.6-luna")
    monkeypatch.setenv("LECTUREPILOT_PRACTICE_EXAM_MODEL", "openai/gpt-5.6-terra")

    planner = PracticeExamPlanner(model_client=_ModelClient([]))

    assert planner.provider_registry.model == "openai/gpt-5.6-terra"


def test_authoritative_evidence_spreads_budget_across_lectures() -> None:
    documents = []
    for index in range(1, 15):
        document = _document()
        document.id = f"canvas-{index:02d}"
        document.lecture_id = f"lecture-{index:02d}"
        document.title = f"Lecture {index:02d}"
        document.sections[0].blocks[0].text = f"Concept {index}. " + "evidence " * 2_000
        documents.append(document)

    evidence, source_ids = authoritative_canvas_evidence(documents)

    assert len(evidence) <= MAX_COURSE_EVIDENCE_CHARS
    assert {source_id.split(":", 1)[0] for source_id in source_ids} == {
        f"lecture-{index:02d}" for index in range(1, 15)
    }

from __future__ import annotations

from copy import deepcopy

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.models import ProviderCapability, ProviderSettings


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
                "reference_answer": (
                    None
                    if index % 2
                    else "Risk is the expected loss; empirical risk is its sample estimate."
                ),
                "source_ids": ["lecture-01:risk:definition"],
                "ppi_pattern_ids": [],
            }
        )
    return {
        "title": "Machine Learning practice exam",
        "instructions": ["Answer every question."],
        "questions": questions,
    }


def _review_payload() -> dict:
    return {
        "reviews": [
            {
                "question_id": f"q-{index:02d}",
                "verdict": "pass",
                "issue": "",
                "source_ids": ["lecture-01:risk:definition"],
                "solved_answer_index": 1 if index % 2 else None,
                "reasoning": "The sample average matches the definition.",
                "evidence_quotes": [
                    {
                        "source_id": "lecture-01:risk:definition",
                        "quote": "Empirical risk averages loss over the observed training sample.",
                    }
                ],
            }
            for index in range(1, 21)
        ]
    }


def _solution_review_payload():
    review = _review_payload()
    review["reviews"] = [r for r in review["reviews"] if r["solved_answer_index"] is None]
    return review


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

    async def complete_exam(self, *, settings, messages, response_format, max_tokens):
        self.messages.append(deepcopy(messages))
        self.response_formats.append(deepcopy(response_format))
        response = self.responses[self.calls]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        return deepcopy(response)

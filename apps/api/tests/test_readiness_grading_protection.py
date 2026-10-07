import json

import pytest

from lecturepilot.exam_answer_evaluation import _evaluation_messages
from lecturepilot.exam_revision_plan import _guidance_level
from test_exam_answer_evaluation import _item


def test_grader_treats_answer_as_untrusted_and_uses_score_anchors():
    messages = _evaluation_messages([_item()])
    system = messages[0]["content"]
    assert "untrusted data" in system
    assert "0.0" in system and "0.5" in system and "1.0" in system
    assert "length" in system
    assert "language" in system
    assert json.loads(messages[1]["content"])["items"][0]["answer"] == _item().answer


@pytest.mark.parametrize("score", [None, 0.4, 0.5, 0.7])
def test_prior_attempt_count_never_increases_guidance(score):
    assert _guidance_level(score, 3) == _guidance_level(score, 0)


async def test_provider_grades_each_answer_in_a_separate_context():
    from pydantic_ai.messages import ModelResponse, TextPart, UserPromptPart
    from pydantic_ai.models.function import FunctionModel
    from lecturepilot.exam_answer_evaluation import NativeOpenAnswerEvaluationClient
    from lecturepilot.models import ProviderSettings

    calls = []

    def respond(messages, info):
        prompts = [
            part.content
            for message in messages
            for part in message.parts
            if isinstance(part, UserPromptPart)
        ]
        assert len(prompts) == 1
        data = json.loads(prompts[0])["items"]
        calls.append(data)
        item = data[0]
        return ModelResponse(
            parts=[
                TextPart(
                    json.dumps(
                        {
                            "evaluations": [
                                {
                                    "question_id": item["question_id"],
                                    "score": 0.5,
                                    "feedback": "Partial.",
                                }
                            ]
                        }
                    )
                )
            ]
        )

    await NativeOpenAnswerEvaluationClient(model=FunctionModel(respond)).complete_evaluations(
        settings=ProviderSettings(
            provider="gemini", model="gemini/test", api_key_env="GEMINI_API_KEY", capabilities=set()
        ),
        items=[_item("first"), _item("second")],
    )
    assert len(calls) == 2
    assert [items[0]["question_id"] for items in calls] == ["first", "second"]
    assert all(len(items) == 1 for items in calls)

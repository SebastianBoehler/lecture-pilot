from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from lecturepilot.exam_answer_evaluation import OpenAnswerEvaluation
from lecturepilot.usage_quota import UsageQuotaExceeded
from test_exam_answer_evaluation import _item


class Quota:
    def __init__(self, *, exhausted=False):
        self.exhausted = exhausted
        self.calls = []

    def reserve_turn(self, **kwargs):
        self.calls.append(("reserve", kwargs))
        if self.exhausted:
            raise UsageQuotaExceeded("Quota exhausted.")
        return True

    def release_turn(self, **kwargs):
        self.calls.append(("release", kwargs))


class Evaluator:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.calls = 0

    async def evaluate(self, *, items):
        self.calls += 1
        if self.fail:
            raise RuntimeError("Provider failed.")
        return [
            OpenAnswerEvaluation(question_id=items[0].question_id, score=0.5, feedback="Partial.")
        ]


@pytest.mark.parametrize("fail", [False, True])
async def test_readiness_releases_concurrent_quota_after_success_or_failure(fail):
    from lecturepilot.readiness_evaluation_request import evaluate_readiness_answers

    quota, evaluator = Quota(), Evaluator(fail=fail)
    app = SimpleNamespace(
        state=SimpleNamespace(
            usage_quota=quota, open_answer_evaluator=evaluator, course_tenant_id="tenant"
        )
    )
    if fail:
        with pytest.raises(RuntimeError):
            await evaluate_readiness_answers(
                app, user_id="user", course_id="course", items=[_item()]
            )
    else:
        await evaluate_readiness_answers(app, user_id="user", course_id="course", items=[_item()])
    assert [call[0] for call in quota.calls] == ["reserve", "release"]
    assert quota.calls[0][1]["reserved_tokens"] > 16_000
    assert quota.calls[1][1]["reserved_tokens"] == quota.calls[0][1]["reserved_tokens"]


async def test_readiness_does_not_call_provider_when_quota_is_exhausted():
    from lecturepilot.readiness_evaluation_request import evaluate_readiness_answers

    quota, evaluator = Quota(exhausted=True), Evaluator()
    app = SimpleNamespace(
        state=SimpleNamespace(
            usage_quota=quota, open_answer_evaluator=evaluator, course_tenant_id="tenant"
        )
    )
    with pytest.raises(HTTPException) as failure:
        await evaluate_readiness_answers(app, user_id="user", course_id="course", items=[_item()])
    assert failure.value.status_code == 429
    assert evaluator.calls == 0

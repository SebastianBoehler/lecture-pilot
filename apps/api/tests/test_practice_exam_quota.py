from test_practice_exam_api import _client, _generate
from lecturepilot.usage_quota import UsageQuotaExceeded
from lecturepilot.model_client import ModelExecutionError


class Quota:
    def __init__(self, exhausted=False):
        self.exhausted = exhausted
        self.reservations = []
        self.releases = []

    def reserve_turn(self, **scope):
        if self.exhausted:
            raise UsageQuotaExceeded("Daily token quota is exhausted.")
        self.reservations.append(scope)
        return True

    def release_turn(self, **scope):
        self.releases.append(scope)


def test_exam_quota_blocks_model_and_records_failed_job(tmp_path):
    client, planner = _client(tmp_path)
    client.app.state.usage_quota = Quota(exhausted=True)
    response = _generate(client)
    assert response.status_code == 429
    assert planner.calls == 0
    from auth_helpers import student_headers

    status = client.get(
        "/courses/martius-ml/practice-exam-generations/status",
        headers={**student_headers("student-a"), "Idempotency-Key": "practice-exam-key-0001"},
    )
    assert status.json()["error_code"] == "quota_exceeded"


def test_exam_reserves_once_for_idempotent_replay_and_releases(tmp_path):
    client, planner = _client(tmp_path)
    quota = client.app.state.usage_quota = Quota()
    assert _generate(client).status_code == 200
    assert _generate(client).status_code == 200
    assert len(quota.reservations) == len(quota.releases) == 1
    assert quota.reservations[0]["reserved_tokens"] > 16000
    assert quota.releases[0]["reserved_tokens"] == quota.reservations[0]["reserved_tokens"]


def test_exam_provider_failure_releases_concurrency(tmp_path):
    client, planner = _client(tmp_path)
    quota = client.app.state.usage_quota = Quota()
    planner.error = ModelExecutionError("provider down")
    assert _generate(client).status_code == 502
    assert len(quota.releases) == 1


def test_exam_generation_has_cumulative_budget_and_deadline(tmp_path, monkeypatch):
    from lecturepilot.authoring_limits import current_authoring_budget
    from lecturepilot import practice_exam_generation

    client, planner = _client(tmp_path)
    original = planner.plan

    async def plan(**kwargs):
        import asyncio

        await asyncio.sleep(0)
        budget = current_authoring_budget()
        assert budget.request_limit == 24
        assert budget.input_tokens_limit == 500_000
        assert budget.output_tokens_limit == 80_000
        return await original(**kwargs)

    planner.plan = plan
    assert _generate(client).status_code == 200
    monkeypatch.setattr(practice_exam_generation, "EXAM_DEADLINE_SECONDS", 0)
    assert _generate(client, key="exam-timeout-regression").status_code == 502

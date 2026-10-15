from __future__ import annotations

from datetime import date
import os
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from auth_helpers import professor_headers, student_headers
from security_db_helpers import seed_account
from lecturepilot.app import create_app
from lecturepilot.courses.course_repository import CourseRepository
from lecturepilot.database import Database
from lecturepilot.llm.model_usage import ModelUsageRecorder, model_usage_scope
from lecturepilot.core.models import CourseWorkspaceSetupInput
from lecturepilot.llm.professor_usage import ProfessorUsageRepository
from lecturepilot.llm.usage_models import ProfessorUsageSummary, UsageLimitSummary, UsageTotals
from lecturepilot.llm.usage_quota import UsageQuota


def test_usage_route_is_professor_only() -> None:
    app = create_app()
    app.state.professor_usage = _FakeProfessorUsage()
    client = TestClient(app)

    allowed = client.get("/admin/usage?days=7", headers=professor_headers())
    denied = client.get("/admin/usage?days=7", headers=student_headers())

    assert allowed.status_code == 200
    assert allowed.json()["totals"]["model_requests"] == 0
    assert denied.status_code == 403
    assert app.state.professor_usage.actor_user_id == "prof01"


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="PostgreSQL test database is required")
def test_professor_usage_contains_only_owned_course_activity() -> None:
    database = Database()
    owner = seed_account(database, "usage-owner", role="lecturer")
    other = seed_account(database, "usage-other", role="lecturer")
    courses = CourseRepository(database)
    owned = courses.create(
        user_id=owner.user_id,
        tenant_id="tenant-tuebingen",
        setup=CourseWorkspaceSetupInput(course_title="Owned Course"),
        default_term="Sommer 2026",
    )
    foreign = courses.create(
        user_id=other.user_id,
        tenant_id="tenant-tuebingen",
        setup=CourseWorkspaceSetupInput(course_title="Foreign Course"),
        default_term="Sommer 2026",
    )
    recorder = ModelUsageRecorder(database, tenant_id="tenant-tuebingen")
    _record(recorder, str(owner.user_id), owned.id, prompt=100, completion=40)
    _record(recorder, str(other.user_id), foreign.id, prompt=900, completion=100)
    quota = UsageQuota(database, enabled=True)
    quota.reserve_turn(tenant_id="tenant-tuebingen", user_id=str(owner.user_id), course_id=owned.id)
    quota.consume_image(
        tenant_id="tenant-tuebingen", user_id=str(owner.user_id), course_id=owned.id
    )
    quota.release_turn(tenant_id="tenant-tuebingen", user_id=str(owner.user_id), course_id=owned.id)

    summary = ProfessorUsageRepository(database).summary(
        actor_user_id=str(owner.user_id), tenant_id="tenant-tuebingen", days=30
    )

    assert summary.totals.model_requests == 1
    assert summary.totals.total_tokens == 140
    assert summary.totals.tutor_turns == 1
    assert summary.totals.images == 1
    assert [course.course_title for course in summary.courses] == ["Owned Course"]


def _record(
    recorder: ModelUsageRecorder,
    user_id: str,
    course_id: str,
    *,
    prompt: int,
    completion: int,
) -> None:
    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=prompt + completion,
        )
    )
    with model_usage_scope(actor_user_id=user_id, course_id=course_id, workload="course_canvas"):
        recorder.record_response(response, model="openai/gpt-5.6-luna")


class _FakeProfessorUsage:
    actor_user_id = ""

    def summary(self, *, actor_user_id: str, tenant_id: str, days: int):
        self.actor_user_id = actor_user_id
        assert tenant_id == "tenant-tuebingen"
        assert days == 7
        return ProfessorUsageSummary(
            period_start=date(2026, 7, 7),
            period_end=date(2026, 7, 13),
            totals=UsageTotals(
                model_requests=0,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cached_input_tokens=0,
                reasoning_tokens=0,
                tutor_turns=0,
                images=0,
            ),
            workloads=[],
            courses=[],
            daily=[],
            limits=UsageLimitSummary(
                turns_per_day=200,
                reserved_tokens_per_day=2_000_000,
                images_per_day=20,
                concurrent_turns=1,
                tokens_per_turn=16_000,
            ),
        )

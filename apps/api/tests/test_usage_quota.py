from __future__ import annotations

import pytest

from lecturepilot.database import Database
from lecturepilot.identity_repository import IdentityRepository
from lecturepilot.university_models import UniversityLoginResult
from lecturepilot.usage_quota import UsageLimits, UsageQuota, UsageQuotaExceeded


def test_durable_agent_and_image_quotas_survive_service_instances() -> None:
    database = Database()
    account = IdentityRepository(database).record_login(
        UniversityLoginResult(username="quota-user", term="Sommer 2026"),
        tenant_id="tenant-tuebingen",
    )
    limits = UsageLimits(
        turns_per_day=2,
        reserved_tokens_per_day=20,
        images_per_day=1,
        concurrent_turns=1,
        tokens_per_turn=10,
    )
    first = UsageQuota(database, limits, enabled=True)
    second = UsageQuota(database, limits, enabled=True)
    scope = {
        "tenant_id": "tenant-tuebingen",
        "user_id": str(account.user_id),
        "course_id": "course-1",
    }

    assert first.reserve_turn(**scope) is True
    with pytest.raises(UsageQuotaExceeded, match="concurrent"):
        second.reserve_turn(**scope)
    first.consume_image(**scope)
    with pytest.raises(UsageQuotaExceeded, match="image"):
        second.consume_image(**scope)
    first.release_turn(**scope)
    assert second.reserve_turn(**scope) is True
    second.release_turn(**scope)
    with pytest.raises(UsageQuotaExceeded, match="quota"):
        first.reserve_turn(**scope)


def test_actual_usage_refunds_tokens_and_failed_image_can_be_retried() -> None:
    database = Database()
    account = IdentityRepository(database).record_login(
        UniversityLoginResult(username="quota-reconciliation", term="Sommer 2026"),
        tenant_id="tenant-tuebingen",
    )
    limits = UsageLimits(
        turns_per_day=5,
        reserved_tokens_per_day=100,
        images_per_day=1,
        concurrent_turns=1,
        tokens_per_turn=40,
    )
    quota = UsageQuota(database, limits, enabled=True)
    scope = dict(tenant_id="tenant-tuebingen", user_id=str(account.user_id), course_id="course-2")
    assert quota.reserve_turn(**scope, reserved_tokens=40)
    quota.consume_image(**scope)
    quota.refund_image(**scope)
    quota.consume_image(**scope)
    quota.release_turn(**scope, reserved_tokens=40, actual_tokens=10)
    assert quota.reserve_turn(**scope, reserved_tokens=80)
    quota.release_turn(**scope, reserved_tokens=80, actual_tokens=50)
    with pytest.raises(UsageQuotaExceeded):
        quota.reserve_turn(**scope, reserved_tokens=50)
    assert quota.reserve_turn(**scope, reserved_tokens=40)
    quota.release_turn(**scope, reserved_tokens=40, actual_tokens=None)
    with pytest.raises(UsageQuotaExceeded):
        quota.reserve_turn(**scope, reserved_tokens=1)


def test_background_exam_reservation_does_not_occupy_or_release_the_tutor_slot():
    database = Database()
    account = IdentityRepository(database).record_login(
        UniversityLoginResult(username="background-quota", term="Sommer 2026"),
        tenant_id="tenant-tuebingen",
    )
    quota = UsageQuota(database, UsageLimits(5, 1000, 1, 1, 10), enabled=True)
    scope = dict(tenant_id="tenant-tuebingen", user_id=str(account.user_id), course_id="course-3")
    assert quota.reserve_turn(**scope, concurrent=False)
    assert quota.reserve_turn(**scope)
    quota.release_turn(**scope, concurrent=False, actual_tokens=2)
    with pytest.raises(UsageQuotaExceeded, match="concurrent"):
        quota.reserve_turn(**scope)
    quota.release_turn(**scope)
    assert quota.reserve_turn(**scope)

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

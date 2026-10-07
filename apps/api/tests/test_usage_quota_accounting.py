from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.dialects.postgresql import dialect
from lecturepilot.usage_quota import UsageQuota, UsageLimits, UsageQuotaExceeded


class Database:
    configured = True

    def __init__(self):
        self.statements = []

    @contextmanager
    def session(self):
        yield self

    def scalar(self, statement):
        self.statements.append(statement)
        return uuid4()

    def execute(self, statement):
        self.statements.append(statement)
        return SimpleNamespace(rowcount=1)


def quota():
    db = Database()
    return UsageQuota(db, UsageLimits(10, 1000, 5, 1, 100), enabled=True), db


def scope():
    return dict(tenant_id="tenant", user_id=str(uuid4()), course_id="course")


def test_custom_reservation_checks_first_request_limit():
    q, db = quota()
    with pytest.raises(UsageQuotaExceeded):
        q.reserve_turn(**scope(), reserved_tokens=1001)
    assert db.statements == []


def test_token_reconciliation_uses_reservation_and_actual_usage():
    q, db = quota()
    q.release_turn(**scope(), reserved_tokens=300, actual_tokens=45)
    compiled = db.statements[0].compile(dialect=dialect())
    assert "reserved_tokens" in str(compiled)
    assert 255 in compiled.params.values()


def test_image_refund_decrements_only_positive_counter():
    q, db = quota()
    q.refund_image(**scope())
    compiled = db.statements[0].compile(dialect=dialect())
    assert "images" in str(compiled)

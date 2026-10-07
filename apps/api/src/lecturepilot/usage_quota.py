from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import os
from uuid import UUID, uuid4

from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import insert

from lecturepilot.database import Database
from lecturepilot.db_models import UsageCounterRecord


class UsageQuotaExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class UsageLimits:
    turns_per_day: int
    reserved_tokens_per_day: int
    images_per_day: int
    concurrent_turns: int
    tokens_per_turn: int

    @classmethod
    def from_env(cls) -> "UsageLimits":
        return cls(
            turns_per_day=_positive_env("LECTUREPILOT_DAILY_AGENT_TURNS", 200),
            reserved_tokens_per_day=_positive_env("LECTUREPILOT_DAILY_RESERVED_TOKENS", 2_000_000),
            images_per_day=_positive_env("LECTUREPILOT_DAILY_IMAGES", 20),
            concurrent_turns=_positive_env("LECTUREPILOT_CONCURRENT_AGENT_TURNS", 1),
            tokens_per_turn=_positive_env("LECTUREPILOT_RESERVED_TOKENS_PER_TURN", 16_000),
        )


class UsageQuota:
    def __init__(
        self,
        database: Database,
        limits: UsageLimits | None = None,
        *,
        enabled: bool | None = None,
    ) -> None:
        self.database = database
        self.limits = limits or UsageLimits.from_env()
        self.enabled = (
            enabled
            if enabled is not None
            else (os.getenv("LECTUREPILOT_ENV", "").strip().lower() == "production")
        )

    def reserve_turn(
        self,
        *,
        tenant_id: str,
        user_id: str,
        course_id: str,
        reserved_tokens: int | None = None,
        usage_date: date | None = None,
        concurrent: bool = True,
    ) -> bool:
        if not self.enabled or not self.database.configured:
            return False
        identity = UUID(user_id)
        limits = self.limits
        reservation = limits.tokens_per_turn if reserved_tokens is None else max(0, reserved_tokens)
        if reservation > limits.reserved_tokens_per_day:
            raise UsageQuotaExceeded("Daily token quota is exhausted.")
        statement = insert(UsageCounterRecord).values(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=identity,
            course_id=course_id,
            usage_date=usage_date or datetime.now(UTC).date(),
            agent_turns=1,
            reserved_tokens=reservation,
            images=0,
            active_turns=int(concurrent),
            updated_at=datetime.now(UTC),
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_daily_usage_scope",
            set_={
                "agent_turns": UsageCounterRecord.agent_turns + 1,
                "reserved_tokens": UsageCounterRecord.reserved_tokens + reservation,
                "active_turns": UsageCounterRecord.active_turns + int(concurrent),
                "updated_at": datetime.now(UTC),
            },
            where=(UsageCounterRecord.agent_turns < limits.turns_per_day)
            & (UsageCounterRecord.reserved_tokens + reservation <= limits.reserved_tokens_per_day)
            & ((UsageCounterRecord.active_turns < limits.concurrent_turns) if concurrent else True),
        ).returning(UsageCounterRecord.id)
        with self.database.session() as session:
            if session.scalar(statement) is None:
                raise UsageQuotaExceeded("Daily or concurrent agent quota is exhausted.")
        return True

    def release_turn(
        self,
        *,
        tenant_id: str,
        user_id: str,
        course_id: str,
        actual_tokens: int | None = None,
        reserved_tokens: int | None = None,
        usage_date: date | None = None,
        concurrent: bool = True,
    ) -> None:
        if not self.enabled or not self.database.configured:
            return
        values = dict(
            active_turns=func.greatest(UsageCounterRecord.active_turns - int(concurrent), 0),
            updated_at=datetime.now(UTC),
        )
        if actual_tokens is not None:
            reservation = (
                self.limits.tokens_per_turn if reserved_tokens is None else reserved_tokens
            )
            values["reserved_tokens"] = func.greatest(
                UsageCounterRecord.reserved_tokens - (reservation - max(0, actual_tokens)), 0
            )
        with self.database.session() as session:
            session.execute(
                update(UsageCounterRecord)
                .where(
                    UsageCounterRecord.tenant_id == tenant_id,
                    UsageCounterRecord.user_id == UUID(user_id),
                    UsageCounterRecord.course_id == course_id,
                    UsageCounterRecord.usage_date == (usage_date or datetime.now(UTC).date()),
                )
                .values(**values)
            )

    def consume_image(
        self, *, tenant_id: str, user_id: str, course_id: str, usage_date: date | None = None
    ) -> None:
        if not self.enabled or not self.database.configured:
            return
        with self.database.session() as session:
            updated = session.execute(
                update(UsageCounterRecord)
                .where(
                    UsageCounterRecord.tenant_id == tenant_id,
                    UsageCounterRecord.user_id == UUID(user_id),
                    UsageCounterRecord.course_id == course_id,
                    UsageCounterRecord.usage_date == (usage_date or datetime.now(UTC).date()),
                    UsageCounterRecord.images < self.limits.images_per_day,
                )
                .values(
                    images=UsageCounterRecord.images + 1,
                    updated_at=datetime.now(UTC),
                )
            )
            if updated.rowcount != 1:
                raise UsageQuotaExceeded("Daily image quota is exhausted.")

    def refund_image(
        self, *, tenant_id: str, user_id: str, course_id: str, usage_date: date | None = None
    ) -> None:
        if not self.enabled or not self.database.configured:
            return
        with self.database.session() as session:
            session.execute(
                update(UsageCounterRecord)
                .where(
                    UsageCounterRecord.tenant_id == tenant_id,
                    UsageCounterRecord.user_id == UUID(user_id),
                    UsageCounterRecord.course_id == course_id,
                    UsageCounterRecord.usage_date == (usage_date or datetime.now(UTC).date()),
                    UsageCounterRecord.images > 0,
                )
                .values(images=UsageCounterRecord.images - 1, updated_at=datetime.now(UTC))
            )


def _positive_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default

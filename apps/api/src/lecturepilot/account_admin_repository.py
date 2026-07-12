from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from lecturepilot.database import Database
from lecturepilot.db_models import AuditEventRecord, TenantMembershipRecord, UserRecord
from lecturepilot.session_store import SessionStore


class AccountAdminError(ValueError):
    pass


class AccountAdminRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def disable_user(self, *, user_id: UUID, actor_id: UUID, tenant_id: str) -> bool:
        with self.database.session() as session:
            user = session.get(UserRecord, user_id)
            membership = session.get(TenantMembershipRecord, (user_id, tenant_id))
            if user is None or membership is None:
                raise AccountAdminError("Account was not found.")
            user.enabled = False
            user.updated_at = datetime.now(UTC)
            session.add(
                AuditEventRecord(
                    tenant_id=tenant_id,
                    actor_user_id=actor_id,
                    event_type="account.disabled",
                    target_type="user",
                    target_id=str(user_id),
                )
            )
        SessionStore(self.database).revoke_user(user_id)
        return True

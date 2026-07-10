from __future__ import annotations

from uuid import UUID

from lecturepilot.database import Database
from lecturepilot.db_models import AuditEventRecord
from lecturepilot.tenancy import TenantContext


def record_audit_event(
    database: Database,
    context: TenantContext,
    *,
    event_type: str,
    target_type: str,
    target_id: str,
    details: dict | None = None,
) -> None:
    if context.auth_mode != "session" or not database.configured:
        return
    with database.session() as session:
        session.add(
            AuditEventRecord(
                tenant_id=context.tenant_id,
                actor_user_id=UUID(context.user_id),
                event_type=event_type,
                target_type=target_type,
                target_id=target_id,
                details=details or {},
            )
        )

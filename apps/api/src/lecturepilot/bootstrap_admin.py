from __future__ import annotations

import argparse
from datetime import UTC, datetime

from sqlalchemy import select

from lecturepilot.database import Database
from lecturepilot.db_models import (
    AuditEventRecord,
    ExternalIdentityRecord,
    TenantMembershipRecord,
)
from lecturepilot.session_store import SessionStore


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Grant the first platform administrator to an existing university identity."
    )
    parser.add_argument("--subject", required=True, help="Exact university username")
    parser.add_argument("--tenant", default="tenant-tuebingen")
    args = parser.parse_args()
    database = Database()
    subject = args.subject.strip().casefold()
    with database.session() as session:
        identity = session.scalar(
            select(ExternalIdentityRecord).where(
                ExternalIdentityRecord.provider == "tuebingen",
                ExternalIdentityRecord.subject == subject,
            )
        )
        if identity is None:
            raise SystemExit("Identity not found. The account must log in once before bootstrap.")
        membership = session.get(TenantMembershipRecord, (identity.user_id, args.tenant))
        if membership is None:
            raise SystemExit("Tenant membership not found for this identity.")
        membership.platform_admin = True
        membership.updated_at = datetime.now(UTC)
        session.add(
            AuditEventRecord(
                tenant_id=args.tenant,
                actor_user_id=identity.user_id,
                event_type="platform_admin.bootstrapped",
                target_type="user",
                target_id=str(identity.user_id),
                details={"operator_cli": True},
            )
        )
        user_id = identity.user_id
    SessionStore(database).revoke_user(user_id)
    print(f"Platform administrator granted for {subject} in {args.tenant}.")


if __name__ == "__main__":
    main()

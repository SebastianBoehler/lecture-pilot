from __future__ import annotations

import argparse
from datetime import UTC, datetime

from sqlalchemy import select

from lecturepilot.database import Database
from lecturepilot.core.db_models import (
    AuditEventRecord,
    ExternalIdentityRecord,
    TenantMembershipRecord,
)
from lecturepilot.identity.session_store import SessionStore
from lecturepilot.identity.local_account_models import LocalCredentialRecord


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Grant an administrator or professor role to an existing verified account."
    )
    parser.add_argument("--subject", required=True, help="Verified university email address")
    parser.add_argument("--tenant", default="tenant-tuebingen")
    parser.add_argument("--role", choices=["tenant_admin", "professor"], default="tenant_admin")
    args = parser.parse_args()
    database = Database()
    subject = args.subject.strip().casefold()
    with database.session() as session:
        credential = session.get(LocalCredentialRecord, subject)
        if credential is None:
            raise SystemExit("Verified account not found. Register and verify your email first.")
        identity = session.scalar(
            select(ExternalIdentityRecord)
            .where(
                ExternalIdentityRecord.user_id == credential.user_id,
            )
            .order_by(ExternalIdentityRecord.created_at)
        )
        if identity is None:
            raise SystemExit("Account identity not found.")
        membership = session.get(TenantMembershipRecord, (identity.user_id, args.tenant))
        if membership is None:
            raise SystemExit("Tenant membership not found for this identity.")
        if args.role == "professor":
            identity.provider_claims = {
                **identity.provider_claims,
                "lecturepilot_account_type": "professor",
            }
        else:
            membership.platform_admin = True
        membership.updated_at = datetime.now(UTC)
        session.add(
            AuditEventRecord(
                tenant_id=args.tenant,
                actor_user_id=identity.user_id,
                event_type=f"{args.role}.bootstrapped",
                target_type="user",
                target_id=str(identity.user_id),
                details={"operator_cli": True},
            )
        )
        user_id = identity.user_id
    SessionStore(database).revoke_user(user_id)
    print(f"{args.role} granted for {subject} in {args.tenant}.")


if __name__ == "__main__":
    main()

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text

from lecturepilot.account_models import ProfessorRequestResponse
from lecturepilot.database import Database
from lecturepilot.db_models import (
    AuditEventRecord,
    ExternalIdentityRecord,
    ProfessorRequestRecord,
    TenantMembershipRecord,
    UserRecord,
)
from lecturepilot.identity_repository import LOCAL_PROFESSOR_PROVIDER
from lecturepilot.session_store import SessionStore


class ApprovalError(ValueError):
    pass


class ApprovalRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def request_professor(self, *, user_id: UUID, tenant_id: str) -> ProfessorRequestResponse:
        with self.database.session() as session:
            session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:request_key))"),
                {"request_key": f"professor:{tenant_id}:{user_id}"},
            )
            membership = session.get(TenantMembershipRecord, (user_id, tenant_id))
            if membership is None:
                raise ApprovalError("Tenant membership is required.")
            if membership.professor_status == "approved":
                raise ApprovalError("Professor access is already approved.")
            existing = session.scalar(
                select(ProfessorRequestRecord).where(
                    ProfessorRequestRecord.user_id == user_id,
                    ProfessorRequestRecord.tenant_id == tenant_id,
                    ProfessorRequestRecord.status == "pending",
                )
            )
            if existing is None:
                existing = ProfessorRequestRecord(user_id=user_id, tenant_id=tenant_id)
                session.add(existing)
                session.flush()
            membership.professor_status = "pending"
            membership.updated_at = datetime.now(UTC)
            session.add(
                AuditEventRecord(
                    tenant_id=tenant_id,
                    actor_user_id=user_id,
                    event_type="professor.requested",
                    target_type="professor_request",
                    target_id=str(existing.id),
                )
            )
            return _request_view(session, existing)

    def pending(self, *, tenant_id: str) -> list[ProfessorRequestResponse]:
        with self.database.session() as session:
            requests = session.scalars(
                select(ProfessorRequestRecord)
                .where(
                    ProfessorRequestRecord.tenant_id == tenant_id,
                    ProfessorRequestRecord.status == "pending",
                )
                .order_by(ProfessorRequestRecord.requested_at)
            ).all()
            return [_request_view(session, request) for request in requests]

    def review(
        self,
        *,
        request_id: UUID,
        reviewer_id: UUID,
        tenant_id: str,
        decision: str,
    ) -> ProfessorRequestResponse:
        if decision not in {"approved", "rejected"}:
            raise ApprovalError("Professor request decision is invalid.")
        with self.database.session() as session:
            request = session.get(ProfessorRequestRecord, request_id)
            if request is None or request.tenant_id != tenant_id:
                raise ApprovalError("Professor request was not found.")
            if request.status != "pending":
                raise ApprovalError("Professor request was already reviewed.")
            membership = session.get(TenantMembershipRecord, (request.user_id, tenant_id))
            if membership is None:
                raise ApprovalError("Professor request membership is missing.")
            now = datetime.now(UTC)
            request.status = decision
            request.reviewed_at = now
            request.reviewed_by = reviewer_id
            membership.professor_status = decision
            membership.updated_at = now
            session.add(
                AuditEventRecord(
                    tenant_id=tenant_id,
                    actor_user_id=reviewer_id,
                    event_type=f"professor.{decision}",
                    target_type="user",
                    target_id=str(request.user_id),
                )
            )
            result = _request_view(session, request)
            target_user_id = request.user_id
        SessionStore(self.database).revoke_user(target_user_id)
        return result

    def disable_user(self, *, user_id: UUID, actor_id: UUID, tenant_id: str) -> bool:
        with self.database.session() as session:
            user = session.get(UserRecord, user_id)
            membership = session.get(TenantMembershipRecord, (user_id, tenant_id))
            if user is None or membership is None:
                raise ApprovalError("Account was not found.")
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


def _request_view(session, request: ProfessorRequestRecord) -> ProfessorRequestResponse:
    identities = session.scalars(
        select(ExternalIdentityRecord).where(
            ExternalIdentityRecord.user_id == request.user_id,
        )
    ).all()
    identity = next(
        (item for item in identities if item.provider == LOCAL_PROFESSOR_PROVIDER),
        identities[0] if identities else None,
    )
    if identity is None:
        raise ApprovalError("Professor request identity is missing.")
    user = session.get(UserRecord, request.user_id)
    return ProfessorRequestResponse(
        id=request.id,
        user_id=request.user_id,
        username=(user.display_name if user else None) or identity.subject,
        email=identity.email,
        status=request.status,
        requested_at=request.requested_at,
        reviewed_at=request.reviewed_at,
    )

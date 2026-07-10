from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pwdlib import PasswordHash
from sqlalchemy import select, text

from lecturepilot.database import Database
from lecturepilot.db_models import (
    AuditEventRecord,
    ExternalIdentityRecord,
    LocalCredentialRecord,
    ProfessorRequestRecord,
    TenantMembershipRecord,
    UserRecord,
)
from lecturepilot.identity_repository import (
    LOCAL_PROFESSOR_PROVIDER,
    AccountView,
    IdentityRepository,
)


class ProfessorAuthenticationError(PermissionError):
    pass


class ProfessorRegistrationError(ValueError):
    pass


_PASSWORD_HASH = PasswordHash.recommended()
_DUMMY_HASH = _PASSWORD_HASH.hash("lecturepilot-dummy-password-not-used-for-login")


class ProfessorIdentityRepository:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.identities = IdentityRepository(database)

    def register(
        self,
        *,
        display_name: str,
        email: str,
        password: str,
        tenant_id: str,
    ) -> AccountView:
        normalized_email = _normalize_email(email)
        encoded_password = _PASSWORD_HASH.hash(password)
        with self.database.session() as session:
            session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:identity_key))"),
                {"identity_key": f"{LOCAL_PROFESSOR_PROVIDER}:{normalized_email}"},
            )
            existing = session.scalar(
                select(ExternalIdentityRecord.id).where(
                    ExternalIdentityRecord.provider == LOCAL_PROFESSOR_PROVIDER,
                    ExternalIdentityRecord.subject == normalized_email,
                )
            )
            if existing is not None:
                raise ProfessorRegistrationError("Professor registration could not be completed.")
            user = UserRecord(display_name=display_name)
            session.add(user)
            session.flush()
            now = datetime.now(UTC)
            session.add_all(
                [
                    ExternalIdentityRecord(
                        user_id=user.id,
                        provider=LOCAL_PROFESSOR_PROVIDER,
                        subject=normalized_email,
                        email=normalized_email,
                        last_login_at=now,
                    ),
                    LocalCredentialRecord(
                        user_id=user.id,
                        password_hash=encoded_password,
                        created_at=now,
                        updated_at=now,
                    ),
                    TenantMembershipRecord(
                        user_id=user.id,
                        tenant_id=tenant_id,
                        professor_status="pending",
                        created_at=now,
                        updated_at=now,
                    ),
                ]
            )
            request = ProfessorRequestRecord(
                user_id=user.id,
                tenant_id=tenant_id,
                status="pending",
                requested_at=now,
            )
            session.add(request)
            session.flush()
            session.add(
                AuditEventRecord(
                    tenant_id=tenant_id,
                    actor_user_id=user.id,
                    event_type="professor.account_registered",
                    target_type="professor_request",
                    target_id=str(request.id),
                )
            )
            user_id = user.id
        return self._account(user_id, tenant_id)

    def authenticate(self, *, email: str, password: str, tenant_id: str) -> AccountView:
        normalized_email = _normalize_email(email)
        with self.database.session() as session:
            identity = session.scalar(
                select(ExternalIdentityRecord).where(
                    ExternalIdentityRecord.provider == LOCAL_PROFESSOR_PROVIDER,
                    ExternalIdentityRecord.subject == normalized_email,
                )
            )
            credential = session.get(LocalCredentialRecord, identity.user_id) if identity else None
            candidate_hash = credential.password_hash if credential else _DUMMY_HASH
            valid = _verify_password(password, candidate_hash)
            user = session.get(UserRecord, identity.user_id) if identity else None
            if not valid or user is None or not user.enabled:
                raise ProfessorAuthenticationError("Email or password is incorrect.")
            identity.last_login_at = datetime.now(UTC)
            session.add(
                AuditEventRecord(
                    tenant_id=tenant_id,
                    actor_user_id=user.id,
                    event_type="auth.professor_login",
                    target_type="user",
                    target_id=str(user.id),
                )
            )
            user_id = user.id
        return self._account(user_id, tenant_id)

    def _account(self, user_id: UUID, tenant_id: str) -> AccountView:
        account = self.identities.account(user_id=user_id, tenant_id=tenant_id)
        if account is None:
            raise ProfessorAuthenticationError("Email or password is incorrect.")
        return account


def _normalize_email(email: str) -> str:
    return email.strip().casefold()


def _verify_password(password: str, encoded_password: str) -> bool:
    try:
        return _PASSWORD_HASH.verify(password, encoded_password)
    except (TypeError, ValueError):
        return False

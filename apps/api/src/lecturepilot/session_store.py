from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets
from uuid import UUID

from sqlalchemy import select, update

from lecturepilot.database import Database
from lecturepilot.db_models import SessionRecord, UserRecord
from lecturepilot.identity_repository import AccountView, IdentityRepository


class SessionStoreError(PermissionError):
    pass


@dataclass(frozen=True)
class IssuedSession:
    token: str
    csrf_token: str
    expires_at: datetime


@dataclass(frozen=True)
class SessionPrincipal:
    session_id: UUID
    account: AccountView


class SessionStore:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.identities = IdentityRepository(database)

    def create(self, account: AccountView, *, ttl_minutes: int) -> IssuedSession:
        token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
        with self.database.session() as session:
            session.add(
                SessionRecord(
                    token_hash=_hash(token),
                    csrf_hash=_hash(csrf_token),
                    user_id=account.user_id,
                    tenant_id=account.tenant_id,
                    expires_at=expires_at,
                )
            )
        return IssuedSession(token=token, csrf_token=csrf_token, expires_at=expires_at)

    def authenticate(self, token: str) -> SessionPrincipal:
        if not token:
            raise SessionStoreError("Authentication is required.")
        with self.database.session() as session:
            record = session.scalar(
                select(SessionRecord).where(SessionRecord.token_hash == _hash(token))
            )
            if record is None or record.revoked_at is not None:
                raise SessionStoreError("Session is invalid or revoked.")
            if _aware(record.expires_at) <= datetime.now(UTC):
                raise SessionStoreError("Session has expired.")
            user = session.get(UserRecord, record.user_id)
            if user is None or not user.enabled:
                raise SessionStoreError("Account is disabled.")
            session_id = record.id
            user_id = record.user_id
            tenant_id = record.tenant_id
        account = self.identities.account(user_id=user_id, tenant_id=tenant_id)
        if account is None:
            raise SessionStoreError("Account membership is unavailable.")
        return SessionPrincipal(session_id=session_id, account=account)

    def verify_csrf(self, token: str, csrf_token: str | None) -> None:
        if not csrf_token:
            raise SessionStoreError("CSRF token is required.")
        with self.database.session() as session:
            record = session.scalar(
                select(SessionRecord).where(SessionRecord.token_hash == _hash(token))
            )
            if record is None or record.revoked_at is not None:
                raise SessionStoreError("Session is invalid or revoked.")
            if not hmac.compare_digest(record.csrf_hash, _hash(csrf_token)):
                raise SessionStoreError("CSRF token is invalid.")

    def revoke(self, token: str | None) -> None:
        if not token:
            return
        with self.database.session() as session:
            record = session.scalar(
                select(SessionRecord).where(SessionRecord.token_hash == _hash(token))
            )
            if record is not None and record.revoked_at is None:
                record.revoked_at = datetime.now(UTC)

    def revoke_user(self, user_id: UUID) -> None:
        with self.database.session() as session:
            session.execute(
                update(SessionRecord)
                .where(SessionRecord.user_id == user_id, SessionRecord.revoked_at.is_(None))
                .values(revoked_at=datetime.now(UTC))
            )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)

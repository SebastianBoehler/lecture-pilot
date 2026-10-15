from datetime import UTC, datetime, timedelta
import hashlib
import secrets

from sqlalchemy import delete, func, select, update

from lecturepilot.core.db_models import (
    AuditEventRecord,
    ExternalIdentityRecord,
    SessionRecord,
    TenantMembershipRecord,
    UserRecord,
)
from lecturepilot.database import Database
from lecturepilot.identity.identity_repository import AccountView, IdentityRepository
from lecturepilot.identity.local_account_models import AccountTokenRecord, LocalCredentialRecord
from lecturepilot.identity.local_passwords import hash_password, verify_password
from lecturepilot.identity.session_store import IssuedSession, SessionStore


class LocalAccounts:
    def __init__(self, database: Database, tenant_id: str = "tenant-tuebingen") -> None:
        self.database = database
        self.tenant_id = tenant_id

    def challenge(self, email: str, purpose: str, password: str | None = None) -> str | None:
        # Calculate outside the transaction. Unknown logins also perform this costly hash.
        password_hash = hash_password(password) if password is not None else None
        token = secrets.token_urlsafe(32)
        with self.database.session() as session:
            session.execute(
                delete(AccountTokenRecord).where(AccountTokenRecord.expires_at <= datetime.now(UTC))
            )
            credential = session.get(LocalCredentialRecord, email)
            if (purpose == "verify" and credential) or (purpose == "reset" and not credential):
                return None
            session.execute(
                select(AccountTokenRecord)
                .where(AccountTokenRecord.email == email)
                .with_for_update()
            )
            record = session.get(AccountTokenRecord, (email, purpose))
            if record is None:
                record = AccountTokenRecord(email=email, purpose=purpose)
                session.add(record)
            record.token_hash = _digest(token)
            record.password_hash = password_hash
            record.expires_at = datetime.now(UTC) + timedelta(minutes=30)
        return token

    def confirm(self, token: str, purpose: str, password: str | None = None) -> None:
        password_hash = hash_password(password) if password is not None else None
        with self.database.session() as session:
            challenge = session.scalar(
                select(AccountTokenRecord)
                .where(
                    AccountTokenRecord.token_hash == _digest(token),
                    AccountTokenRecord.purpose == purpose,
                )
                .with_for_update()
            )
            if challenge is None or _aware(challenge.expires_at) <= datetime.now(UTC):
                raise ValueError("This email link is invalid or expired. Request a new link.")
            credential = session.scalar(
                select(LocalCredentialRecord)
                .where(LocalCredentialRecord.email == challenge.email)
                .with_for_update()
            )
            if purpose == "verify":
                if credential is not None:
                    raise ValueError("This email address is already registered.")
                # A verified mailbox can reclaim exactly one prior account with that email.
                identities = session.scalars(
                    select(ExternalIdentityRecord).where(
                        func.lower(ExternalIdentityRecord.email) == challenge.email,
                        ExternalIdentityRecord.provider == "tuebingen",
                    )
                ).all()
                if len(identities) > 1:
                    raise ValueError("Multiple existing accounts use this email. Contact support.")
                if identities:
                    user = session.get(UserRecord, identities[0].user_id)
                    if user is None or not user.enabled:
                        raise ValueError("This account is disabled. Contact support.")
                else:
                    user = UserRecord()
                    session.add(user)
                    session.flush()
                    session.add(
                        ExternalIdentityRecord(
                            user_id=user.id,
                            provider="local",
                            subject=challenge.email,
                            email=challenge.email,
                            provider_claims={},
                        )
                    )
                    session.add(TenantMembershipRecord(user_id=user.id, tenant_id=self.tenant_id))
                session.add(
                    LocalCredentialRecord(
                        email=challenge.email,
                        user_id=user.id,
                        password_hash=challenge.password_hash,
                    )
                )
            else:
                if credential is None:
                    raise ValueError("This email link is invalid or expired.")
                credential.password_hash = password_hash
                # Password replacement and revocation commit in the same transaction.
                session.execute(
                    update(SessionRecord)
                    .where(
                        SessionRecord.user_id == credential.user_id,
                        SessionRecord.revoked_at.is_(None),
                    )
                    .values(revoked_at=datetime.now(UTC))
                )
            user_id = user.id if purpose == "verify" else credential.user_id
            session.add(
                AuditEventRecord(
                    tenant_id=self.tenant_id,
                    actor_user_id=user_id,
                    event_type="auth.email_verified"
                    if purpose == "verify"
                    else "auth.password_reset",
                    target_type="user",
                    target_id=str(user_id),
                    details={"provider": "local"},
                )
            )
            session.delete(challenge)

    def sign_in(
        self,
        email: str,
        password: str,
        session_store: SessionStore,
        *,
        ttl_minutes: int,
    ) -> tuple[AccountView, IssuedSession] | None:
        with self.database.session() as session:
            credential = session.scalar(
                select(LocalCredentialRecord)
                .where(LocalCredentialRecord.email == email)
                .with_for_update()
            )
            if credential is None:
                hash_password(password)
                return None
            if not verify_password(password, credential.password_hash):
                return None
            account = IdentityRepository(self.database).account(
                user_id=credential.user_id, tenant_id=self.tenant_id
            )
            if account is None:
                return None
            issued = session_store.create(
                account, ttl_minutes=ttl_minutes, database_session=session
            )
            session.add(
                AuditEventRecord(
                    tenant_id=self.tenant_id,
                    actor_user_id=account.user_id,
                    event_type="auth.login",
                    target_type="user",
                    target_id=str(account.user_id),
                    details={"provider": "local"},
                )
            )
            return account, issued


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)

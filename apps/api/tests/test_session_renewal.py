from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from lecturepilot.app import create_app
from lecturepilot.db_models import (
    Base,
    ExternalIdentityRecord,
    SessionRecord,
    TenantMembershipRecord,
    UserRecord,
)
from lecturepilot.identity_repository import IdentityRepository
from lecturepilot.session_auth import SESSION_COOKIE_NAME
from lecturepilot.session_store import SessionStore


def test_active_cookie_session_renews_near_idle_timeout(monkeypatch, tmp_path) -> None:
    client, database = _session_client(monkeypatch, tmp_path, ttl_minutes=60)
    original_expiry = datetime.now(UTC) + timedelta(minutes=5)
    with database.session() as session:
        record = session.scalar(select(SessionRecord))
        assert record is not None
        record.expires_at = original_expiry

    response = client.get("/me")

    assert response.status_code == 200
    assert "Max-Age=3600" in response.headers["set-cookie"]
    with database.session() as session:
        renewed = session.scalar(select(SessionRecord))
        assert renewed is not None
        assert renewed.expires_at.replace(tzinfo=UTC) > original_expiry + timedelta(minutes=50)


def test_activity_cannot_renew_past_absolute_session_lifetime(monkeypatch, tmp_path) -> None:
    client, database = _session_client(
        monkeypatch,
        tmp_path,
        ttl_minutes=60,
        max_lifetime_minutes=60,
    )
    with database.session() as session:
        record = session.scalar(select(SessionRecord))
        assert record is not None
        record.created_at = datetime.now(UTC) - timedelta(minutes=61)
        record.expires_at = datetime.now(UTC) + timedelta(minutes=5)

    response = client.get("/me")

    assert response.status_code == 401
    assert "set-cookie" not in response.headers


def _session_client(
    monkeypatch,
    tmp_path,
    *,
    ttl_minutes: int,
    max_lifetime_minutes: int = 1_440,
) -> tuple[TestClient, "_SqliteDatabase"]:
    monkeypatch.setenv("LECTUREPILOT_ENV", "test")
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "session")
    monkeypatch.setenv("LECTUREPILOT_SESSION_TTL_MINUTES", str(ttl_minutes))
    monkeypatch.setenv(
        "LECTUREPILOT_SESSION_MAX_LIFETIME_MINUTES",
        str(max_lifetime_minutes),
    )
    app = create_app()
    database = _SqliteDatabase(tmp_path / "sessions.sqlite")
    Base.metadata.create_all(database.engine)
    app.state.database = database
    app.state.session_store = SessionStore(database)
    user_id = uuid4()
    with database.session() as session:
        session.add(UserRecord(id=user_id, enabled=True))
        session.add(
            ExternalIdentityRecord(
                user_id=user_id,
                provider="tuebingen",
                subject="student01",
                provider_claims={},
                course_sync_status="ready",
            )
        )
        session.add(TenantMembershipRecord(user_id=user_id, tenant_id="tenant-tuebingen"))
    account = IdentityRepository(database).account(
        user_id=user_id,
        tenant_id="tenant-tuebingen",
    )
    assert account is not None
    issued = app.state.session_store.create(account, ttl_minutes=ttl_minutes)
    client = TestClient(app)
    client.cookies.set(SESSION_COOKIE_NAME, issued.token)
    return client, database


class _SqliteDatabase:
    def __init__(self, path) -> None:
        self.engine = create_engine(f"sqlite:///{path}")
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    @property
    def configured(self) -> bool:
        return True

    @contextmanager
    def session(self):
        session = self._sessions()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

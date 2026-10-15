from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from lecturepilot.app import create_app
from lecturepilot.core.db_models import Base, SessionRecord
from lecturepilot.identity.local_account_models import AccountTokenRecord, LocalCredentialRecord
from lecturepilot.identity.local_accounts import LocalAccounts
from lecturepilot.identity.session_store import SessionStore
from test_session_renewal import _SqliteDatabase


@pytest.fixture(params=["sqlite", "postgres"])
def accounts(monkeypatch, tmp_path, request):
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "session")
    app = create_app()
    if request.param == "postgres":
        database = app.state.database
        if not database.configured:
            pytest.skip("Dedicated PostgreSQL test database is not configured.")
    else:
        database = _SqliteDatabase(tmp_path / "accounts.sqlite")
        Base.metadata.create_all(database.engine)
    app.state.database = database
    app.state.session_store = SessionStore(database)
    sent = []
    monkeypatch.setattr(
        "lecturepilot.identity.local_account_routes.send_account_email",
        lambda email, purpose, token: sent.append((email, purpose, token)),
    )
    return TestClient(app), database, sent


def register(client, sent, email="student@student.uni-tuebingen.de"):
    result = client.post("/auth/register", json={"email": email, "password": "a separate password"})
    assert result.status_code == 200, result.text
    assert "token" not in result.text
    return sent[-1][2]


def test_verified_account_cookie_login_and_reset(accounts):
    client, database, sent = accounts
    token = register(client, sent)
    payload = {"email": sent[-1][0], "password": "a separate password"}
    assert client.post("/auth/login", json=payload).status_code == 401
    assert client.post("/auth/verify", json={"token": token}).status_code == 200
    assert client.post("/auth/verify", json={"token": token}).status_code == 400
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["roles"] == ["student"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert client.get("/me").status_code == 200
    with database.session() as session:
        credential = session.scalar(select(LocalCredentialRecord))
        assert "a separate password" not in credential.password_hash
    assert client.post("/auth/password-reset", json={"email": payload["email"]}).status_code == 200
    reset = sent[-1][2]
    assert (
        client.post(
            "/auth/password-reset/confirm",
            json={"token": reset, "password": "a different password"},
        ).status_code
        == 200
    )
    assert client.get("/me").status_code == 401
    client.cookies.clear()
    assert client.post("/auth/login", json=payload).status_code == 401
    payload["password"] = "a different password"
    assert client.post("/auth/login", json=payload).status_code == 200
    with database.session() as session:
        assert any(item.revoked_at for item in session.scalars(select(SessionRecord)))


def test_rejects_zdv_payload_external_email_and_self_assigned_roles(accounts):
    client, _, _ = accounts
    assert (
        client.post("/auth/login", json={"username": "student01", "password": "zdv"}).status_code
        == 422
    )
    assert (
        client.post(
            "/auth/register", json={"email": "s@example.com", "password": "a separate password"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/auth/register",
            json={
                "email": "s@uni-tuebingen.de",
                "password": "a separate password",
                "roles": ["professor"],
            },
        ).status_code
        == 422
    )


def test_expired_verification_and_unknown_reset(accounts):
    client, database, sent = accounts
    token = register(client, sent)
    with database.session() as session:
        session.scalar(select(AccountTokenRecord)).expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )
    assert client.post("/auth/verify", json={"token": token}).status_code == 400
    before = len(sent)
    assert (
        client.post("/auth/password-reset", json={"email": "absent@uni-tuebingen.de"}).status_code
        == 200
    )
    assert len(sent) == before
    assert (
        LocalAccounts(database).sign_in(
            "absent@uni-tuebingen.de", "wrong", client.app.state.session_store, ttl_minutes=60
        )
        is None
    )


def test_reclaims_only_matching_verified_legacy_account(accounts):
    from lecturepilot.core.db_models import (
        ExternalIdentityRecord,
        TenantMembershipRecord,
        UserRecord,
    )

    client, database, sent = accounts
    with database.session() as session:
        user = UserRecord(display_name="Existing lecturer")
        session.add(user)
        session.flush()
        user_id = user.id
        session.add(
            ExternalIdentityRecord(
                user_id=user.id,
                provider="tuebingen",
                subject="old-zdv-name",
                email="teacher@uni-tuebingen.de",
                provider_claims={"alma_current_role": "lecturer"},
            )
        )
        session.add(TenantMembershipRecord(user_id=user.id, tenant_id="tenant-tuebingen"))
    token = register(client, sent, "teacher@uni-tuebingen.de")
    assert client.post("/auth/verify", json={"token": token}).status_code == 200
    response = client.post(
        "/auth/login", json={"email": "teacher@uni-tuebingen.de", "password": "a separate password"}
    )
    assert response.status_code == 200
    assert response.json()["roles"] == ["professor"]
    assert response.json()["username"] == "old-zdv-name"
    assert client.get("/me").json()["user_id"] == str(user_id)


def test_validation_never_echoes_passwords_and_auth_rejects_cross_site(accounts):
    client, _, _ = accounts
    response = client.post("/auth/login", json={"username": "old", "password": "private-secret"})
    assert response.status_code == 422
    assert "private-secret" not in response.text
    response = client.post(
        "/auth/register",
        headers={"Origin": "https://attacker.example"},
        json={"email": "new@uni-tuebingen.de", "password": "a separate password"},
    )
    assert response.status_code == 403


def test_duplicate_registration_does_not_replace_password(accounts):
    client, _, sent = accounts
    token = register(client, sent)
    assert client.post("/auth/verify", json={"token": token}).status_code == 200
    before = len(sent)
    assert (
        client.post(
            "/auth/register", json={"email": sent[-1][0], "password": "attacker chosen password"}
        ).status_code
        == 200
    )
    assert len(sent) == before
    assert (
        client.post(
            "/auth/login", json={"email": sent[-1][0], "password": "a separate password"}
        ).status_code
        == 200
    )


def test_failed_smtp_is_actionable_without_exposing_token(accounts, monkeypatch):
    from lecturepilot.identity.account_email import AccountEmailError

    client, _, _ = accounts

    def fail(*_args):
        raise AccountEmailError("Account email could not be sent. Please try again later.")

    monkeypatch.setattr("lecturepilot.identity.local_account_routes.send_account_email", fail)
    response = client.post(
        "/auth/register", json={"email": "new@uni-tuebingen.de", "password": "a separate password"}
    )
    assert response.status_code == 503
    assert "token" not in response.text


def test_operator_grants_professor_role_to_a_verified_account(accounts, monkeypatch):
    from lecturepilot.bootstrap_admin import main

    client, database, sent = accounts
    email = "teacher@uni-tuebingen.de"
    token = register(client, sent, email)
    assert client.post("/auth/verify", json={"token": token}).status_code == 200
    monkeypatch.setattr("lecturepilot.bootstrap_admin.Database", lambda: database)
    monkeypatch.setattr("sys.argv", ["bootstrap", "--subject", email, "--role", "professor"])
    main()
    response = client.post("/auth/login", json={"email": email, "password": "a separate password"})
    assert response.status_code == 200
    assert response.json()["roles"] == ["professor"]

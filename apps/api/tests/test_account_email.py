import smtplib

import pytest

from lecturepilot.identity.account_email import AccountEmailError, send_account_email


def test_missing_email_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("LECTUREPILOT_SMTP_HOST", raising=False)
    with pytest.raises(AccountEmailError, match="SMTP"):
        send_account_email("student@uni-tuebingen.de", "verify", "secret-token")


def test_smtp_requires_tls_before_authentication_and_sends_fragment_link(monkeypatch):
    calls = []

    class Relay:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def ehlo(self):
            calls.append("ehlo")

        def starttls(self, *, context):
            assert context.check_hostname
            calls.append("tls")

        def login(self, username, password):
            assert calls[-1] == "ehlo" and "tls" in calls
            calls.append("login")

        def send_message(self, message):
            calls.append(message)

    monkeypatch.setattr(smtplib, "SMTP", Relay)
    monkeypatch.setenv("LECTUREPILOT_SMTP_HOST", "smtp.example.org")
    monkeypatch.setenv("LECTUREPILOT_SMTP_FROM", "noreply@example.org")
    monkeypatch.setenv("LECTUREPILOT_PUBLIC_URL", "https://lecturepilot.example.org")
    monkeypatch.setenv("LECTUREPILOT_SMTP_USERNAME", "mailer")
    monkeypatch.setenv("LECTUREPILOT_SMTP_PASSWORD", "mail-secret")
    send_account_email("student@uni-tuebingen.de", "verify", "secret-token")
    assert calls[:4] == ["ehlo", "tls", "ehlo", "login"]
    assert "/#auth=verify&token=secret-token" in calls[-1].get_content()
    assert "mail-secret" not in str(calls[-1])

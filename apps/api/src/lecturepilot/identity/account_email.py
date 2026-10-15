"""SMTP delivery fails explicitly; account tokens never appear in API responses or logs."""

from email.message import EmailMessage
import os
import smtplib
import ssl
from urllib.parse import urlencode, urlsplit


class AccountEmailError(RuntimeError):
    pass


def send_account_email(email: str, purpose: str, token: str) -> None:
    host = os.getenv("LECTUREPILOT_SMTP_HOST", "").strip()
    sender = os.getenv("LECTUREPILOT_SMTP_FROM", "").strip()
    origin = os.getenv("LECTUREPILOT_PUBLIC_URL", "").strip().rstrip("/")
    parsed = urlsplit(origin)
    if not host or not sender or parsed.scheme != "https" or not parsed.hostname:
        raise AccountEmailError(
            "Email delivery requires SMTP and an HTTPS LECTUREPILOT_PUBLIC_URL."
        )
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise AccountEmailError(
            "LECTUREPILOT_PUBLIC_URL must not contain credentials or query data."
        )
    link = origin + "/#" + urlencode({"auth": purpose, "token": token})
    action = (
        "Verify your LecturePilot account"
        if purpose == "verify"
        else "Reset your LecturePilot password"
    )
    message = EmailMessage()
    message["Subject"] = action
    message["From"] = sender
    message["To"] = email
    message.set_content(
        f"{action}\n\n{link}\n\nThis link expires in 30 minutes and works once.\n"
        "Use a separate LecturePilot password. Never enter your ZDV password.\n"
        "If you did not request this email, ignore it."
    )
    try:
        port = int(os.getenv("LECTUREPILOT_SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            username = os.getenv("LECTUREPILOT_SMTP_USERNAME", "")
            if username:
                smtp.login(username, os.getenv("LECTUREPILOT_SMTP_PASSWORD", ""))
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        raise AccountEmailError("Account email could not be sent. Please try again later.") from exc

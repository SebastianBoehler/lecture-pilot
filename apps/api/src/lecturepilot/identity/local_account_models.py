"""Private local credentials and single-use email challenges."""

from datetime import datetime
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from lecturepilot.core.db_base import Base


class LocalCredentialRecord(Base):
    __tablename__ = "local_credentials"

    email: Mapped[str] = mapped_column(String(200), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    password_hash: Mapped[str] = mapped_column(String(300), nullable=False)


class AccountTokenRecord(Base):
    __tablename__ = "account_tokens"

    email: Mapped[str] = mapped_column(String(200), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(20), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(300))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EmailInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=200)

    @field_validator("email")
    @classmethod
    def university_email(cls, value: str) -> str:
        value = value.strip().casefold()
        local, separator, domain = value.partition("@")
        if (
            not separator
            or not local
            or "@" in domain
            or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}", local)
            or local.startswith(".")
            or local.endswith(".")
            or ".." in local
            or not re.fullmatch(
                r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*uni-tuebingen\.de", domain
            )
        ):
            raise ValueError("Use your University of Tübingen email address.")
        return value


class PasswordLoginInput(EmailInput):
    password: SecretStr = Field(min_length=1, max_length=500)


class RegistrationInput(EmailInput):
    password: SecretStr = Field(min_length=12, max_length=500)


class TokenInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: SecretStr = Field(min_length=32, max_length=200)


class ResetPasswordInput(TokenInput):
    password: SecretStr = Field(min_length=12, max_length=500)

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from lecturepilot.models import Course, TenantRole


ProfessorStatus = Literal["not_requested", "pending", "approved", "rejected"]
AccountType = Literal["student", "professor"]


class TuebingenLoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: SecretStr = Field(min_length=1, max_length=500)
    term: str = Field(default="Sommer 2026", min_length=1, max_length=80)


class LocalProfessorRegistrationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: SecretStr = Field(min_length=15, max_length=128)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Display name is required.")
        return normalized


class LocalProfessorLoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class LoginResult(BaseModel):
    username: str
    email: str | None = None
    term: str
    tenant_id: str = "tenant-tuebingen"
    account_type: AccountType = "student"
    roles: list[TenantRole] = Field(default_factory=list)
    professor_status: ProfessorStatus = "not_requested"
    csrf_token: str | None = Field(default=None, min_length=32, max_length=200)
    access_token: str | None = None
    courses: list[Course]


class AccountResponse(BaseModel):
    user_id: UUID
    username: str
    email: str | None = None
    tenant_id: str
    account_type: AccountType
    roles: list[TenantRole]
    professor_status: ProfessorStatus
    courses: list[Course]
    csrf_token: str | None = Field(default=None, min_length=32, max_length=200)


TuebingenLoginResult = LoginResult


class ProfessorRequestResponse(BaseModel):
    id: UUID
    user_id: UUID
    username: str
    email: str | None = None
    status: ProfessorStatus
    requested_at: datetime
    reviewed_at: datetime | None = None


class AccountDisabledResponse(BaseModel):
    user_id: UUID
    disabled: bool

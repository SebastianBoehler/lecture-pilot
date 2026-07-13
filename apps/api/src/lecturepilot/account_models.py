from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr

from lecturepilot.models import Course, TenantRole
from lecturepilot.university_models import ExternalCourseCandidate


AccountType = Literal["student", "professor"]


class TuebingenLoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: SecretStr = Field(min_length=1, max_length=500)
    term: str = Field(default="Sommer 2026", min_length=1, max_length=80)


class LoginResult(BaseModel):
    username: str
    display_name: str | None = None
    email: str | None = None
    term: str
    tenant_id: str = "tenant-tuebingen"
    account_type: AccountType = "student"
    university_role: str | None = Field(default=None, max_length=120)
    roles: list[TenantRole] = Field(default_factory=list)
    csrf_token: str | None = Field(default=None, min_length=32, max_length=200)
    access_token: str | None = None
    courses: list[Course]
    university_courses: list[ExternalCourseCandidate] = Field(default_factory=list)


class AccountResponse(BaseModel):
    user_id: UUID
    username: str
    display_name: str | None = None
    email: str | None = None
    tenant_id: str
    account_type: AccountType
    university_role: str | None = Field(default=None, max_length=120)
    roles: list[TenantRole]
    courses: list[Course]
    csrf_token: str | None = Field(default=None, min_length=32, max_length=200)
    university_courses: list[ExternalCourseCandidate] = Field(default_factory=list)


TuebingenLoginResult = LoginResult


class AccountDisabledResponse(BaseModel):
    user_id: UUID
    disabled: bool

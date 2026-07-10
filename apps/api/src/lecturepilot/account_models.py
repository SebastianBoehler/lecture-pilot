from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr

from lecturepilot.models import Course, TenantRole


ProfessorStatus = Literal["not_requested", "pending", "approved", "rejected"]


class TuebingenLoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: SecretStr = Field(min_length=1, max_length=500)
    term: str = Field(default="Sommer 2026", min_length=1, max_length=80)


class TuebingenLoginResult(BaseModel):
    username: str
    email: str | None = None
    term: str
    tenant_id: str = "tenant-tuebingen"
    roles: list[TenantRole] = Field(default_factory=lambda: [TenantRole.STUDENT])
    professor_status: ProfessorStatus = "not_requested"
    csrf_token: str | None = Field(default=None, min_length=32, max_length=200)
    access_token: str | None = None
    courses: list[Course]


class AccountResponse(BaseModel):
    user_id: UUID
    username: str
    email: str | None = None
    tenant_id: str
    roles: list[TenantRole]
    professor_status: ProfessorStatus
    courses: list[Course]
    csrf_token: str | None = Field(default=None, min_length=32, max_length=200)


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

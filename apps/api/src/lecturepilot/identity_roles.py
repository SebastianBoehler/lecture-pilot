from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal


ALMA_CURRENT_ROLE_CLAIM = "alma_current_role"
ALMA_AVAILABLE_ROLES_CLAIM = "alma_available_roles"


def alma_account_type(current_role: str | None) -> Literal["student", "professor"]:
    """Classify a non-student as a candidate; database approval remains the permission boundary."""
    if not current_role or _normalize(current_role) == "student":
        return "student"
    return "professor"


def identity_account_type(
    *, provider: str, provider_claims: Mapping[str, Any] | None
) -> Literal["student", "professor"]:
    if provider != "tuebingen":
        return "student"
    current_role = (provider_claims or {}).get(ALMA_CURRENT_ROLE_CLAIM)
    return alma_account_type(current_role if isinstance(current_role, str) else None)


def alma_current_role(provider_claims: Mapping[str, Any] | None) -> str | None:
    value = (provider_claims or {}).get(ALMA_CURRENT_ROLE_CLAIM)
    return value if isinstance(value, str) and value.strip() else None


def alma_available_roles(provider_claims: Mapping[str, Any] | None) -> list[str]:
    value = (provider_claims or {}).get(ALMA_AVAILABLE_ROLES_CLAIM)
    if not isinstance(value, list):
        return []
    return [role for role in value if isinstance(role, str) and role.strip()]


def _normalize(value: str) -> str:
    return " ".join(value.split()).casefold()

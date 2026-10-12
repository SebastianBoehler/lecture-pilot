from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from lecturepilot.models import TenantRole, UserProfile


class TenantAccessError(PermissionError):
    """Raised when tenant membership or role policy denies an operation."""


_COURSE_MANAGEMENT_ROLES = frozenset({TenantRole.TENANT_ADMIN, TenantRole.PROFESSOR})


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    user_id: str
    roles: frozenset[TenantRole]
    course_ids: frozenset[str] = frozenset()
    auth_mode: str = "session"

    @classmethod
    def from_profile(cls, profile: UserProfile, *, tenant_id: str) -> "TenantContext":
        roles = frozenset(
            membership.role
            for membership in profile.memberships
            if membership.tenant_id == tenant_id
        )
        if not roles:
            raise TenantAccessError("User is not a member of this tenant.")
        return cls(tenant_id=tenant_id, user_id=profile.id, roles=roles)


def assert_same_tenant(context: TenantContext, *, resource_tenant_id: str) -> None:
    if context.tenant_id != resource_tenant_id:
        raise TenantAccessError("Resource does not belong to the active tenant.")


def assert_can_manage_course(context: TenantContext, *, course_tenant_id: str) -> None:
    assert_same_tenant(context, resource_tenant_id=course_tenant_id)
    if context.roles.isdisjoint(_COURSE_MANAGEMENT_ROLES):
        raise TenantAccessError("Course management requires a professor or tenant_admin role.")


def tenant_storage_prefix(tenant_id: str) -> str:
    return f"tenants/{_tenant_hash(tenant_id)}"


def _tenant_hash(tenant_id: str) -> str:
    return sha256(tenant_id.encode("utf-8")).hexdigest()[:16]

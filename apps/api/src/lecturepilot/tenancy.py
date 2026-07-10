from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re

from lecturepilot.models import TenantRole, UserProfile


class TenantAccessError(PermissionError):
    """Raised when tenant membership or role policy denies an operation."""


_CACHE_PART_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")
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


def assert_can_upload_course_material(context: TenantContext, *, course_tenant_id: str) -> None:
    assert_can_manage_course(context, course_tenant_id=course_tenant_id)


def assert_can_view_progress(
    context: TenantContext,
    *,
    learner_user_id: str,
    progress_tenant_id: str,
) -> None:
    assert_same_tenant(context, resource_tenant_id=progress_tenant_id)
    if context.user_id == learner_user_id:
        return
    raise TenantAccessError("Learner progress belongs only to the active learner.")


def tenant_storage_prefix(tenant_id: str) -> str:
    return f"tenants/{_tenant_hash(tenant_id)}"


def tenant_cache_key(tenant_id: str, *, namespace: str, key: str) -> str:
    if not _CACHE_PART_RE.fullmatch(namespace) or not _CACHE_PART_RE.fullmatch(key):
        raise TenantAccessError("Cache keys must be bounded safe identifiers.")
    return f"t:{_tenant_hash(tenant_id)}:{namespace}:{key}"


def _tenant_hash(tenant_id: str) -> str:
    return sha256(tenant_id.encode("utf-8")).hexdigest()[:16]

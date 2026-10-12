import pytest

from lecturepilot.core.models import TenantMembership, TenantRole, UserProfile
from lecturepilot.identity.tenancy import (
    TenantAccessError,
    TenantContext,
    assert_can_manage_course,
    tenant_storage_prefix,
)
from lecturepilot.core.workspace import WorkspacePolicy, WorkspacePolicyError


def test_profile_membership_creates_tenant_context() -> None:
    profile = UserProfile(
        id="user-prof-1",
        username="prof01",
        email="prof01@example.edu",
        memberships=[
            TenantMembership(tenant_id="tenant-tuebingen", role=TenantRole.PROFESSOR),
            TenantMembership(tenant_id="tenant-demo", role=TenantRole.STUDENT),
        ],
    )

    context = TenantContext.from_profile(profile, tenant_id="tenant-tuebingen")

    assert context.user_id == "user-prof-1"
    assert context.tenant_id == "tenant-tuebingen"
    assert context.roles == frozenset({TenantRole.PROFESSOR})


def test_tenant_context_denies_unknown_membership() -> None:
    profile = UserProfile(
        id="user-student-1",
        username="student01",
        memberships=[TenantMembership(tenant_id="tenant-demo", role=TenantRole.STUDENT)],
    )

    with pytest.raises(TenantAccessError):
        TenantContext.from_profile(profile, tenant_id="tenant-tuebingen")


def test_professor_can_manage_course_in_own_tenant() -> None:
    context = TenantContext(
        tenant_id="tenant-tuebingen",
        user_id="user-prof-1",
        roles=frozenset({TenantRole.PROFESSOR}),
    )

    assert_can_manage_course(context, course_tenant_id="tenant-tuebingen")


def test_tenant_admin_can_manage_course() -> None:
    context = TenantContext(
        tenant_id="tenant-tuebingen",
        user_id="user-admin-1",
        roles=frozenset({TenantRole.TENANT_ADMIN}),
    )

    assert_can_manage_course(context, course_tenant_id="tenant-tuebingen")


def test_student_cannot_manage_course() -> None:
    context = TenantContext(
        tenant_id="tenant-tuebingen",
        user_id="user-student-1",
        roles=frozenset({TenantRole.STUDENT}),
    )

    with pytest.raises(TenantAccessError):
        assert_can_manage_course(context, course_tenant_id="tenant-tuebingen")


def test_cross_tenant_access_is_denied_even_for_professor() -> None:
    context = TenantContext(
        tenant_id="tenant-tuebingen",
        user_id="user-prof-1",
        roles=frozenset({TenantRole.PROFESSOR}),
    )

    with pytest.raises(TenantAccessError):
        assert_can_manage_course(context, course_tenant_id="tenant-other")


def test_tenant_storage_prefix_does_not_expose_tenant_slug() -> None:
    prefix = tenant_storage_prefix("tenant-tuebingen")

    assert prefix.startswith("tenants/")
    assert "tenant-tuebingen" not in prefix
    assert prefix == tenant_storage_prefix("tenant-tuebingen")
    assert prefix != tenant_storage_prefix("tenant-other")


def test_course_material_uploads_are_tenant_prefixed_and_allowlisted() -> None:
    policy = WorkspacePolicy()

    checked = [
        policy.validate_course_material_upload(
            tenant_id="tenant-tuebingen",
            path=path,
            size_bytes=32_000,
        )
        for path in (
            "lectures/03/source.tex",
            "lectures/03/slides.pdf",
            "lectures/03/figure.svg",
            "lectures/03/demo.mp4",
            "lectures/03/notebook.ipynb",
        )
    ]

    assert [item.kind for item in checked] == ["latex", "pdf", "svg", "video", "notebook"]
    assert all(item.path.startswith("tenants/") for item in checked)
    assert checked[0].path.endswith("/course-materials/lectures/03/source.tex")
    assert all("tenant-tuebingen" not in item.path for item in checked)


@pytest.mark.parametrize(
    ("path", "size"),
    [
        ("lectures/03/source.exe", 100),
        ("../source.tex", 100),
        ("lectures/03/source.pdf", 101 * 1024 * 1024),
        ("lectures/03/demo.mp4", 501 * 1024 * 1024),
    ],
)
def test_course_material_uploads_reject_unsafe_files(path: str, size: int) -> None:
    policy = WorkspacePolicy()

    with pytest.raises(WorkspacePolicyError):
        policy.validate_course_material_upload(
            tenant_id="tenant-tuebingen",
            path=path,
            size_bytes=size,
        )

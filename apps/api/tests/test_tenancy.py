import pytest

from lecturepilot.models import TenantMembership, TenantRole, UserProfile
from lecturepilot.tenancy import (
    TenantAccessError,
    TenantContext,
    assert_can_manage_course,
    assert_can_upload_course_material,
    assert_can_view_progress,
    tenant_cache_key,
    tenant_storage_prefix,
)
from lecturepilot.workspace import WorkspacePolicy, WorkspacePolicyError


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


def test_professor_can_manage_course_and_upload_material_in_own_tenant() -> None:
    context = TenantContext(
        tenant_id="tenant-tuebingen",
        user_id="user-prof-1",
        roles=frozenset({TenantRole.PROFESSOR}),
    )

    assert_can_manage_course(context, course_tenant_id="tenant-tuebingen")
    assert_can_upload_course_material(context, course_tenant_id="tenant-tuebingen")


def test_tenant_admin_can_manage_course_upload_and_review_progress() -> None:
    context = TenantContext(
        tenant_id="tenant-tuebingen",
        user_id="user-admin-1",
        roles=frozenset({TenantRole.TENANT_ADMIN}),
    )

    assert_can_manage_course(context, course_tenant_id="tenant-tuebingen")
    assert_can_upload_course_material(context, course_tenant_id="tenant-tuebingen")
    assert_can_view_progress(
        context,
        learner_user_id="user-student-1",
        progress_tenant_id="tenant-tuebingen",
    )


def test_student_cannot_manage_course_or_upload_material() -> None:
    context = TenantContext(
        tenant_id="tenant-tuebingen",
        user_id="user-student-1",
        roles=frozenset({TenantRole.STUDENT}),
    )

    with pytest.raises(TenantAccessError):
        assert_can_manage_course(context, course_tenant_id="tenant-tuebingen")
    with pytest.raises(TenantAccessError):
        assert_can_upload_course_material(context, course_tenant_id="tenant-tuebingen")


def test_cross_tenant_access_is_denied_even_for_professor() -> None:
    context = TenantContext(
        tenant_id="tenant-tuebingen",
        user_id="user-prof-1",
        roles=frozenset({TenantRole.PROFESSOR}),
    )

    with pytest.raises(TenantAccessError):
        assert_can_manage_course(context, course_tenant_id="tenant-other")


def test_progress_access_allows_self_or_teaching_roles_only() -> None:
    student = TenantContext(
        tenant_id="tenant-tuebingen",
        user_id="user-student-1",
        roles=frozenset({TenantRole.STUDENT}),
    )
    tutor = TenantContext(
        tenant_id="tenant-tuebingen",
        user_id="user-tutor-1",
        roles=frozenset({TenantRole.TUTOR}),
    )

    assert_can_view_progress(
        student,
        learner_user_id="user-student-1",
        progress_tenant_id="tenant-tuebingen",
    )
    assert_can_view_progress(
        tutor,
        learner_user_id="user-student-1",
        progress_tenant_id="tenant-tuebingen",
    )

    with pytest.raises(TenantAccessError):
        assert_can_view_progress(
            student,
            learner_user_id="user-student-2",
            progress_tenant_id="tenant-tuebingen",
        )


def test_progress_access_denies_cross_tenant_records() -> None:
    tutor = TenantContext(
        tenant_id="tenant-tuebingen",
        user_id="user-tutor-1",
        roles=frozenset({TenantRole.TUTOR}),
    )

    with pytest.raises(TenantAccessError):
        assert_can_view_progress(
            tutor,
            learner_user_id="user-student-1",
            progress_tenant_id="tenant-other",
        )


def test_tenant_storage_prefix_does_not_expose_tenant_slug() -> None:
    prefix = tenant_storage_prefix("tenant-tuebingen")

    assert prefix.startswith("tenants/")
    assert "tenant-tuebingen" not in prefix
    assert prefix == tenant_storage_prefix("tenant-tuebingen")
    assert prefix != tenant_storage_prefix("tenant-other")


def test_cache_key_is_tenant_scoped_and_validated() -> None:
    key = tenant_cache_key("tenant-tuebingen", namespace="courses", key="martius-ml")

    assert key.startswith("t:")
    assert "tenant-tuebingen" not in key
    assert key.endswith(":courses:martius-ml")

    with pytest.raises(TenantAccessError):
        tenant_cache_key("tenant-tuebingen", namespace="courses", key="bad\nkey")


def test_course_material_uploads_are_tenant_prefixed_and_allowlisted() -> None:
    policy = WorkspacePolicy()

    checked = policy.validate_course_material_upload(
        tenant_id="tenant-tuebingen",
        path="lectures/03/source.tex",
        size_bytes=32_000,
    )

    assert checked.kind == "latex"
    assert checked.path.startswith("tenants/")
    assert checked.path.endswith("/course-materials/lectures/03/source.tex")
    assert "tenant-tuebingen" not in checked.path


@pytest.mark.parametrize(
    ("path", "size"),
    [
        ("lectures/03/source.exe", 100),
        ("lectures/03/source.svg", 100),
        ("../source.tex", 100),
        ("lectures/03/source.pdf", 101 * 1024 * 1024),
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

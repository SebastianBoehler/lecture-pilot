from lecturepilot.app import create_app
from lecturepilot.identity_repository import IdentityRepository
from lecturepilot.university_models import ExternalCourseSource, UniversityLoginResult
from security_db_helpers import candidate


def test_course_sync_exposes_each_source_without_waiting_for_the_other() -> None:
    repository = IdentityRepository(create_app().state.database)
    initial = UniversityLoginResult(
        username="student",
        term="Sommer 2026",
        alma_current_role="student",
        alma_available_roles=["student"],
    )

    loading = repository.begin_login(initial, tenant_id="tenant-tuebingen", sync_id="fresh")

    assert loading.university_course_source_statuses == {
        ExternalCourseSource.ALMA: "loading",
        ExternalCourseSource.ILIAS: "loading",
    }
    ilias_course = candidate("ilias", "crs:partial", title="Partial Course")
    assert repository.record_course_sync_source(
        initial.model_copy(
            update={
                "courses": [ilias_course],
                "sources_checked": {ExternalCourseSource.ILIAS},
            }
        ),
        tenant_id="tenant-tuebingen",
        sync_id="fresh",
        source=ExternalCourseSource.ILIAS,
    )

    partial = repository.account(user_id=loading.user_id, tenant_id="tenant-tuebingen")

    assert partial is not None
    assert partial.university_course_sync_status == "loading"
    assert partial.university_course_source_statuses == {
        ExternalCourseSource.ALMA: "loading",
        ExternalCourseSource.ILIAS: "ready",
    }
    assert [course.title for course in partial.university_courses] == ["Partial Course"]

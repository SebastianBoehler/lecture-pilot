from lecturepilot.course_workspace import merge_course_workspace, resolve_course_workspace
from lecturepilot.models import CourseWorkspaceSetupInput


def _workspace(target, **values):
    setup = CourseWorkspaceSetupInput(
        course_title="Medizinische Visualisierung", target=target, **values
    )
    return resolve_course_workspace(setup, professor="Prof", term="WS 2026")


def test_setup_target_is_stored_and_survives_later_schedule_updates():
    created = _workspace("full-course")
    assert created.setup_target == "full-course"
    assert [lecture.title for lecture in created.lectures] == ["Lecture 01"]
    updated = merge_course_workspace(created, _workspace("single-lecture", lecture_title="Intro"))
    assert updated.setup_target == "full-course"

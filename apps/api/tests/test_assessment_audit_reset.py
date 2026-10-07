from lecturepilot.learner_workspace_reset import LearnerWorkspaceResetInput, reset_learner_workspace
from lecturepilot.storage_layout import StorageLayout


def test_progress_reset_deletes_private_answer_quotations(tmp_path):
    layout = StorageLayout(tmp_path)
    path = layout.user_lecture_root("student", "course", "lecture") / "assessment-audit.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("private answer excerpt")
    request = LearnerWorkspaceResetInput(
        reset_canvas=False,
        reset_course_memory=False,
        reset_practice_exams=False,
    )
    reset_learner_workspace(layout=layout, user_id="student", course_id="course", request=request)
    assert path.exists()
    reset_learner_workspace(
        layout=layout,
        user_id="student",
        course_id="course",
        request=request.model_copy(update={"reset_progress": True}),
    )
    assert not path.exists()

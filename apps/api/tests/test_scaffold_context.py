from lecturepilot.exam_revision_plan import ExamRevisionTask
from lecturepilot.model_client import _messages
from lecturepilot.models import AgentTurnInput, AttendanceStatus, CanvasState


def test_model_prompt_includes_active_scaffold_policy() -> None:
    messages = _messages(
        AgentTurnInput(
            user_id="student01",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance=AttendanceStatus.UNKNOWN,
            message="Help me review this failed readiness task.",
            canvas_state=CanvasState(focused_section_id="bayes-formula"),
            readiness_task=_revision_task().model_dump(mode="json"),
        )
    )

    user_prompt = messages[1]["content"]
    assert "Active readiness scaffold policy:" in user_prompt
    assert "task_id: lecture-03-q1-review" in user_prompt
    assert "profile: worked_example" in user_prompt
    assert "expected_evidence: Name evidence as the normalizer." in user_prompt
    assert "Do not ask for a full independent solution" in user_prompt


def _revision_task() -> ExamRevisionTask:
    return ExamRevisionTask(
        id="lecture-03-q1-review",
        question_id="lecture-03:q1",
        kind="review_wrong_mc",
        guidance_level="scaffolded",
        lecture_id="lecture-03",
        lecture_title="Bayes",
        section_id="bayes-formula",
        section_title="Bayes formula",
        prompt="Which term normalizes the posterior?",
        source_ref="Lecture03-eng.tex frames 5-6",
        rubric=["Name evidence as the normalizer."],
        expected_evidence="Name evidence as the normalizer.",
        next_action="Review Bayes formula, then answer a follow-up without seeing the options.",
    )

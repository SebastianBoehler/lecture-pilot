from pathlib import Path

from auth_helpers import professor_headers
from lecturepilot.agent_context_models import AgentConversationMessage
from lecturepilot.coaching_state_models import CoachingProgress
from test_learner_lesson_state_routes import COURSE_ID, _client, _write_progress


def test_professor_analytics_never_exposes_private_tutor_messages(tmp_path: Path) -> None:
    client = _client(tmp_path)
    progress = CoachingProgress.empty(course_id=COURSE_ID, lecture_id="lecture-open")
    progress.session_goal = "Private goal"
    progress.messages = [
        AgentConversationMessage(role="user", content="private learner message"),
        AgentConversationMessage(role="assistant", content="private tutor message"),
    ]
    _write_progress(client, "student-a", progress)

    response = client.get(
        f"/admin/courses/{COURSE_ID}/lectures/lecture-open/analytics",
        headers=professor_headers("prof-a"),
    )
    serialized = response.text

    assert response.status_code == 200
    assert "private learner message" not in serialized
    assert "private tutor message" not in serialized
    assert '"messages"' not in serialized

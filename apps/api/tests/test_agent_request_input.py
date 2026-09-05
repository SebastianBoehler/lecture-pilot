import pytest
from pydantic import ValidationError

from lecturepilot.models import AgentTurnRequest


@pytest.mark.parametrize("message", ["", " ", "\t\n", "\u2003\u00a0", "x" * 4001])
def test_agent_request_rejects_blank_or_oversized_messages(message):
    with pytest.raises(ValidationError):
        AgentTurnRequest(
            course_id="course", lecture_id="lecture", attendance="unknown", message=message
        )


def test_agent_request_preserves_multiline_attempt_formatting():
    message = "  x = input image\n  y = label\n"
    request = AgentTurnRequest(
        course_id="course", lecture_id="lecture", attendance="unknown", message=message
    )
    assert request.message == message

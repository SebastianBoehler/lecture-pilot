import base64
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pydantic_ai.messages import BinaryContent, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.function import FunctionModel

from auth_helpers import student_headers
from lecturepilot.app import create_app
from lecturepilot.core.models import AgentTurnRequest, ProviderSettings
from lecturepilot.tutor.native_tutor import native_tutor_turn
from test_strict_model_payload import _payload, _turn


JPEG = b"\xff\xd8\xffcamera-frame\xff\xd9"
FRAME = base64.b64encode(JPEG).decode()


def request(**overrides):
    return AgentTurnRequest(
        **{
            "course_id": "course",
            "lecture_id": "lecture",
            "attendance": "present",
            "message": "Where did my derivation go wrong?",
            "camera_frame": FRAME,
            **overrides,
        }
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"camera_frame": "https://example.com/frame.jpg"},
        {"camera_frame": "AAAA" * 200_001},
        {"checkpoint_gate_id": "checkpoint"},
        {"readiness_task_id": "readiness"},
    ],
)
def test_camera_frame_request_rejects_invalid_input_and_assessment(overrides):
    with pytest.raises(ValidationError):
        request(**overrides)


async def test_camera_frame_reaches_current_model_prompt_without_serializing_into_turn():
    camera_turn = request().for_user("learner")
    assert "camera_frame" not in camera_turn.model_dump()
    turn = _turn().model_copy(update={"camera_frame": camera_turn.camera_frame})

    def respond(messages, info):
        prompt = messages[-1].parts[-1]
        assert isinstance(prompt, UserPromptPart)
        assert prompt.content[0] == "Student answer"
        assert prompt.content[1] == BinaryContent(data=JPEG, media_type="image/jpeg")
        return ModelResponse(parts=[TextPart(json.dumps(_payload()))])

    await native_tutor_turn(
        settings=ProviderSettings(
            provider="openai", model="openai/gpt-6", api_key_env="KEY", capabilities=set()
        ),
        turn=turn,
        messages=[{"role": "user", "content": "Student answer"}],
        model=FunctionModel(respond),
    )


@pytest.mark.parametrize("endpoint", ["/agent/turn", "/agent/turn/stream"])
def test_assessment_rejection_does_not_echo_the_frame(endpoint):
    payload = request().model_dump(exclude={"camera_frame"})
    payload.update(camera_frame=FRAME, checkpoint_gate_id="checkpoint")
    response = TestClient(create_app()).post(
        endpoint, json=payload, headers=student_headers("learner")
    )

    assert response.status_code == 422
    assert "only available in tutor chat" in response.text
    assert FRAME not in response.text


def test_recall_requires_an_image_and_section():
    with pytest.raises(ValidationError):
        request(recall_publication_version=1, camera_frame=None)
    with pytest.raises(ValidationError):
        request(recall_publication_version=1)
    turn = request(
        recall_publication_version=1, canvas_state={"focused_section_id": "intro"}
    ).for_user("learner")
    assert turn.recall_publication_version == 1


async def test_recall_uses_only_focused_teaching_and_an_image_without_tools():
    from lecturepilot.canvas.canvas_models import CanvasBlock
    from lecturepilot.llm.model_client import NativeModelClient

    turn = _turn(active_gate=False, bound_check=False)
    turn.canvas_context.sections[0].blocks.append(
        CanvasBlock(id="hidden-check", type="checkpoint", text="Practice task wording.")
    )
    turn.canvas_state.focused_section_id = "mechanism"
    turn.recall_publication_version = 1
    turn.camera_frame = JPEG

    def respond(messages, info):
        assert not info.function_tools
        assert set(info.output_tools) == set()
        from pydantic_ai.messages import CachePoint

        prompt = [
            item
            for message in messages
            for part in message.parts
            if isinstance(part, UserPromptPart)
            for item in (part.content if isinstance(part.content, list) else [part.content])
        ]
        assert "cause produces the effect" in prompt[0]
        assert "Practice task wording." not in prompt[0]
        assert isinstance(prompt[1], CachePoint)
        assert prompt[2] == "Give feedback on the attached recall attempt in English."
        assert prompt[3].data == JPEG
        assert info.model_settings["max_tokens"] == 1024
        assert info.model_settings["openai_prompt_cache_key"].startswith("lp:recall:")
        return ModelResponse(parts=[TextPart(json.dumps({"message": "Specify the boundary."}))])

    result = await NativeModelClient(model=FunctionModel(respond)).complete_turn(
        settings=ProviderSettings(
            provider="openai", model="openai/gpt-6", api_key_env="KEY", capabilities=set()
        ),
        turn=turn,
        tool_executor=object(),
    )
    assert result.message == "Specify the boundary."
    assert not result.canvas_commands
    assert result.quality_gate is None

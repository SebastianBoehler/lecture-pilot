from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)

from lecturepilot.authoring_models import AuthoringMetrics
from lecturepilot.canvas_internal_serialization import canvas_document_internal_payload
from lecturepilot.durable_files import atomic_write_json

if TYPE_CHECKING:
    from lecturepilot.authoring_job import AuthoringJob


class AuthoringStateError(RuntimeError):
    pass


class AuthoringState(BaseModel):
    identity: str
    messages: list[dict] = Field(default_factory=list)
    metrics: AuthoringMetrics = Field(default_factory=AuthoringMetrics)
    accepted_digest: str | None = None
    failures: dict[str, int] = Field(default_factory=dict)
    completed: bool = False


def state_identity(job: AuthoringJob) -> str:
    payload = {
        "schema": 2,
        "source": canvas_document_internal_payload(job.source),
        "source_revision": job.source_revision,
        "design_revision": job.design.revision,
        "model": job.settings.model,
        "language": job.output_language,
    }
    return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def load_state(job: AuthoringJob) -> AuthoringState:
    path = job.root / "session.json"
    identity = state_identity(job)
    if not path.exists():
        return AuthoringState(identity=identity)
    state = AuthoringState.model_validate_json(path.read_text())
    if state.identity != identity:
        raise AuthoringStateError("Authoring session source, design, model, or language changed.")
    state.metrics.resumes += 1
    return state


def save_state(root: Path, state: AuthoringState, messages: list[ModelMessage]) -> None:
    state.messages = ModelMessagesTypeAdapter.dump_python(messages, mode="json")
    atomic_write_json(root / "session.json", state.model_dump(mode="json"))


def resume_messages(state: AuthoringState) -> list[ModelMessage]:
    messages = ModelMessagesTypeAdapter.validate_python(state.messages)
    # An interrupted tool batch has uncertain side effects. Never blindly replay an
    # edit: return uncertainty to the model, which can inspect the atomic draft files.
    pending: dict[str, ToolCallPart] = {}
    for message in messages:
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ToolCallPart):
                    pending[part.tool_call_id] = part
        elif isinstance(message, ModelRequest):
            for part in message.parts:
                call_id = getattr(part, "tool_call_id", None)
                if call_id:
                    pending.pop(call_id, None)
    if pending:
        messages.append(
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        tool_name=part.tool_name,
                        tool_call_id=part.tool_call_id,
                        content="Worker interrupted; operation may have completed. Read current draft before editing.",
                        outcome="failed",
                    )
                    for part in pending.values()
                ]
            )
        )
    return messages

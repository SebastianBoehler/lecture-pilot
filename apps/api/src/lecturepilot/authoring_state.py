from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
)

from lecturepilot.authoring_models import AuthoringMetrics
from lecturepilot.canvas_internal_serialization import canvas_document_internal_payload
from lecturepilot.durable_files import atomic_write_json

if TYPE_CHECKING:
    from lecturepilot.authoring_job import AuthoringJob


class AuthoringStateError(RuntimeError):
    pass


class AuthoringCritique(BaseModel):
    """The single critic pass: notes get one repair each and are never reviewed again."""

    notes: dict[str, list[str]] = Field(default_factory=dict)
    # Checkpoint conflicts left after the one teaching repair: shown, never section-repaired.
    disputed: dict[str, list[str]] = Field(default_factory=dict)
    repaired: list[str] = Field(default_factory=list)


class AuthoringState(BaseModel):
    identity: str
    messages: list[dict] = Field(default_factory=list)
    history_count: int = 0
    metrics: AuthoringMetrics = Field(default_factory=AuthoringMetrics)
    accepted_digest: str | None = None
    failures: dict[str, int] = Field(default_factory=dict)
    completed: bool = False
    # Sessions saved before the single-critic workflow have none and are critiqued once.
    critique: AuthoringCritique | None = None


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
    state = read_state(job.root)
    if state.identity != identity:
        # Saved drafts are resume points only for the exact inputs that produced them. A changed
        # source document (e.g. OCR became available), design or model starts the job afresh.
        _discard_resume_state(job.root)
        return AuthoringState(identity=identity)
    state.metrics.resumes += 1
    return state


def _discard_resume_state(root: Path) -> None:
    (root / "session.json").unlink(missing_ok=True)
    for name in ("history", "draft", "evidence"):
        shutil.rmtree(root / name, ignore_errors=True)


def read_state(root: Path) -> AuthoringState:
    state = AuthoringState.model_validate_json((root / "session.json").read_text())
    sealed = [
        json.loads((root / "history" / f"{index:08d}.json").read_text())
        for index in range(state.history_count)
    ]
    state.messages = sealed + state.messages
    return state


def save_state(root: Path, state: AuthoringState, messages: list[ModelMessage]) -> None:
    # Only the trailing request/response can gain parts. Sealed messages never change.
    delta = ModelMessagesTypeAdapter.dump_python(messages[state.history_count :], mode="json")
    state.messages = state.messages[: state.history_count] + delta
    sealed_count = max(0, len(messages) - 2)
    for index in range(state.history_count, sealed_count):
        atomic_write_json(root / "history" / f"{index:08d}.json", state.messages[index])
    state.history_count = sealed_count
    payload = state.model_dump(mode="json", exclude={"messages"})
    payload["messages"] = state.messages[sealed_count:]
    atomic_write_json(root / "session.json", payload)

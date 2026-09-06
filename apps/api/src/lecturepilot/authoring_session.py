"""Bind successive HTTP repair attempts to one private framework session."""

import json
import re

from lecturepilot.authoring_state import AuthoringStateError
from lecturepilot.durable_files import atomic_write_json
from lecturepilot.storage_layout import safe_id


RESUMABLE_AUTHORING_ERRORS = {
    "model_execution_error",
    "authoring_stalled_error",
    "unexpected_model_behavior",
}


def session_root(layout, course_id, lecture_id, generation_id):
    directory = layout.course_root(course_id) / "builder" / "authoring-jobs" / safe_id(lecture_id)
    root = directory / safe_id(generation_id)
    reference = root / "session-reference.json"
    if reference.exists():
        try:
            payload = json.loads(reference.read_text())
            identity = payload.get("generation_id") if isinstance(payload, dict) else None
        except (OSError, ValueError) as exc:
            raise AuthoringStateError("Authoring session reference could not be read.") from exc
        if not isinstance(identity, str) or not re.fullmatch(r"[a-f0-9]{32}", identity):
            raise AuthoringStateError("Invalid authoring session reference.")
        return directory / identity
    return root


def bind_session(layout, ownership, previous_generation_id=None):
    current = session_root(
        layout, ownership.course_id, ownership.lecture_id, ownership.generation_id
    )
    if previous_generation_id is None:
        return current
    previous = session_root(
        layout, ownership.course_id, ownership.lecture_id, previous_generation_id
    )
    if current != previous:
        atomic_write_json(current / "session-reference.json", {"generation_id": previous.name})
    return previous


def has_resumable_session(layout, job):
    if job.error_code not in RESUMABLE_AUTHORING_ERRORS:
        return False
    try:
        return (
            session_root(layout, job.course_id, job.lecture_id, job.generation_id) / "session.json"
        ).is_file()
    except (OSError, AuthoringStateError):
        return False

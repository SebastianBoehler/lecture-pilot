from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.course_practice_design_store import PracticeDesignStore
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.durable_files import ensure_durable_directory, fsync_directory
from lecturepilot.storage_layout import StorageLayout, safe_id


class CanvasGenerationOwnership(BaseModel):
    schema_version: int = 1
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    token: str = Field(pattern=r"^[a-f0-9]{32}$")
    sequence: int = Field(ge=1)
    generation_id: str = Field(min_length=1, max_length=160)
    attempt: int = Field(ge=1)
    practice_design_revision: str = Field(pattern=r"^[a-f0-9]{64}$")


class CanvasGenerationOwnershipError(RuntimeError):
    pass


def begin_owned_generation_source(
    layout: StorageLayout,
    course_root: Path,
    source_document: Callable[[str, str], CanvasDocument],
    *,
    course_id: str,
    lecture_id: str,
    generation_id: str,
    attempt: int,
    expected_repair_source_revision: str | None = None,
) -> tuple[CanvasDocument, str, PracticeDesign, CanvasGenerationOwnership]:
    with locked_course_state(course_root):
        source, revision, design = _approved_source(
            layout, source_document, course_id=course_id, lecture_id=lecture_id
        )
        if (
            expected_repair_source_revision is not None
            and expected_repair_source_revision != revision
        ):
            raise CanvasGenerationOwnershipError(
                "Lecture source changed after this failure. Generate a new draft before repairing it."
            )
        path = ownership_path(layout, course_id, lecture_id)
        previous = _read(path)
        owner = CanvasGenerationOwnership(
            course_id=course_id,
            lecture_id=lecture_id,
            token=uuid4().hex,
            sequence=(previous.sequence + 1) if previous else 1,
            generation_id=generation_id,
            attempt=attempt,
            practice_design_revision=design.revision,
        )
        _write(path, owner)
        return source, revision, design, owner


def require_generation_practice_design(
    layout: StorageLayout,
    course_root: Path,
    source_document: Callable[[str, str], CanvasDocument],
    *,
    course_id: str,
    lecture_id: str,
) -> PracticeDesign:
    with locked_course_state(course_root):
        _, _, design = _approved_source(
            layout, source_document, course_id=course_id, lecture_id=lecture_id
        )
        return design


def require_generation_ownership(
    layout: StorageLayout,
    expected: CanvasGenerationOwnership,
) -> None:
    current = _read(ownership_path(layout, expected.course_id, expected.lecture_id))
    if current != expected:
        raise CanvasGenerationOwnershipError("Canvas generation was superseded by a newer request.")


def ownership_path(layout: StorageLayout, course_id: str, lecture_id: str) -> Path:
    return (
        layout.course_root(course_id)
        / "builder"
        / "generation-ownership"
        / f"{safe_id(lecture_id)}.json"
    )


def _approved_source(
    layout: StorageLayout,
    source_document: Callable[[str, str], CanvasDocument],
    *,
    course_id: str,
    lecture_id: str,
) -> tuple[CanvasDocument, str, PracticeDesign]:
    source = source_document(course_id, lecture_id)
    revision = lecture_source_revision(layout, course_id=course_id, lecture_id=lecture_id)
    if revision is None:
        raise CanvasGenerationOwnershipError("Draft source provenance is unavailable.")
    design = PracticeDesignStore(layout).require_approved(
        course_id=course_id, lecture_id=lecture_id, source_revision=revision
    )
    return source, revision, design


def _read(path: Path) -> CanvasGenerationOwnership | None:
    if not path.exists():
        return None
    try:
        return CanvasGenerationOwnership.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise CanvasGenerationOwnershipError(
            "Stored canvas generation ownership is invalid."
        ) from exc


def _write(path: Path, owner: CanvasGenerationOwnership) -> None:
    ensure_durable_directory(path.parent)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(owner.model_dump_json(indent=2))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)

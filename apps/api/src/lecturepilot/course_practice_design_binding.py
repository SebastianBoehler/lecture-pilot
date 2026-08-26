from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.course_practice_design_store import (
    PracticeDesignApprovalRequired,
    PracticeDesignStale,
    PracticeDesignStore,
)
from lecturepilot.course_practice_design_validation import (
    validate_canvas_practice_contract,
    validate_learning_map_practice_contract,
)
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.durable_files import ensure_durable_directory, fsync_directory
from lecturepilot.storage_layout import StorageLayout


class PracticeDesignBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    practice_design_revision: str = Field(pattern=r"^[a-f0-9]{64}$")


class PracticeDesignBindingError(ValueError):
    pass


def binding_path(canvas_dir: Path) -> Path:
    return canvas_dir / "practice-design-binding.json"


def read_practice_design_binding(canvas_dir: Path) -> PracticeDesignBinding:
    path = binding_path(canvas_dir)
    if not path.exists():
        raise PracticeDesignBindingError(
            "This canvas draft has no practice-design binding. Regenerate the draft."
        )
    try:
        return PracticeDesignBinding.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise PracticeDesignBindingError(
            "Stored practice-design binding is invalid. Regenerate the draft."
        ) from exc


def write_practice_design_binding(
    canvas_dir: Path, design: PracticeDesign
) -> PracticeDesignBinding:
    binding = PracticeDesignBinding(
        source_revision=design.source_revision,
        practice_design_revision=design.revision,
    )
    path = binding_path(canvas_dir)
    ensure_durable_directory(path.parent)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(binding.model_dump_json(indent=2))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)
    return binding


def validate_practice_design_binding(
    binding: PracticeDesignBinding,
    design: PracticeDesign,
    *,
    source_revision: str,
) -> None:
    if (
        binding.source_revision != source_revision
        or design.source_revision != source_revision
        or binding.practice_design_revision != design.revision
    ):
        raise PracticeDesignBindingError(
            "The practice-design binding is stale. Regenerate the draft."
        )


def require_bound_practice_design(
    layout: StorageLayout,
    canvas_dir: Path,
    *,
    course_id: str,
    lecture_id: str,
    source_revision: str,
) -> PracticeDesign:
    binding = read_practice_design_binding(canvas_dir)
    try:
        design = PracticeDesignStore(layout).require_approved(
            course_id=course_id,
            lecture_id=lecture_id,
            source_revision=source_revision,
            design_revision=binding.practice_design_revision,
        )
    except (PracticeDesignApprovalRequired, PracticeDesignStale) as exc:
        raise PracticeDesignBindingError(
            "The practice-design binding is no longer approved. Regenerate the draft."
        ) from exc
    validate_practice_design_binding(binding, design, source_revision=source_revision)
    return design


def validate_bound_canvas_draft(
    layout: StorageLayout, canvas_dir: Path, document, *, course_id: str, lecture_id: str
) -> None:
    source_revision = lecture_source_revision(layout, course_id=course_id, lecture_id=lecture_id)
    if source_revision is None:
        raise PracticeDesignBindingError("Draft source provenance is unavailable.")
    validate_canvas_practice_contract(
        document,
        require_bound_practice_design(
            layout,
            canvas_dir,
            course_id=course_id,
            lecture_id=lecture_id,
            source_revision=source_revision,
        ),
    )


def validate_bound_learning_map(
    layout: StorageLayout,
    canvas_dir: Path,
    learning_map,
    *,
    course_id: str,
    lecture_id: str,
    source_revision: str,
) -> PracticeDesign:
    design = require_bound_practice_design(
        layout,
        canvas_dir,
        course_id=course_id,
        lecture_id=lecture_id,
        source_revision=source_revision,
    )
    validate_learning_map_practice_contract(learning_map, design)
    return design

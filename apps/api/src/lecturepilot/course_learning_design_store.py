from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from lecturepilot.canvas_markdown import read_document_source
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.canvas_snapshot import locked_canvas_paths
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.course_learning_design_models import (
    LearningDesignApproval,
    LearningDesignReview,
    LearningDesignUpdate,
)
from lecturepilot.durable_files import ensure_durable_directory, fsync_directory
from lecturepilot.learning_map import LearningMap, build_learning_map
from lecturepilot.storage_layout import StorageLayout
from lecturepilot.course_update_recovery import locked_course_state


class LearningDesignError(ValueError):
    pass


class LearningDesignStaleError(LearningDesignError):
    pass


class LearningDesignUnavailableError(LearningDesignError):
    pass


class LearningDesignApprovalRequiredError(LearningDesignError):
    pass


class CourseLearningDesignStore:
    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def read(self, *, course_id: str, lecture_id: str) -> LearningDesignReview:
        with self._locked_draft(course_id, lecture_id) as draft_dir:
            return _current_review(self.layout, draft_dir, course_id, lecture_id)

    def update(
        self,
        *,
        course_id: str,
        lecture_id: str,
        update: LearningDesignUpdate,
    ) -> LearningDesignReview:
        with self._locked_draft(course_id, lecture_id) as draft_dir:
            current = _current_review(self.layout, draft_dir, course_id, lecture_id)
            _require_request_version(current, update.draft_digest, update.source_revision)
            learning_map = _apply_update(current.learning_map, update)
            changed = current.model_copy(
                update={
                    "learning_map": learning_map,
                    "warnings": learning_design_warnings(learning_map),
                    "approval": None,
                }
            )
            _write_review(review_path(draft_dir), changed)
            return changed

    def approve(
        self,
        *,
        course_id: str,
        lecture_id: str,
        draft_digest: str,
        source_revision: str,
        approved_by: str,
    ) -> LearningDesignReview:
        with self._locked_draft(course_id, lecture_id) as draft_dir:
            current = _current_review(self.layout, draft_dir, course_id, lecture_id)
            _require_request_version(current, draft_digest, source_revision)
            approval = LearningDesignApproval(
                approved_by=approved_by,
                approved_at=datetime.now(UTC),
                draft_digest=current.draft_digest,
                source_revision=current.source_revision,
                learning_map_revision=current.learning_map.revision,
            )
            approved = current.model_copy(update={"approval": approval})
            _write_review(review_path(draft_dir), approved)
            return approved

    @contextmanager
    def _locked_draft(self, course_id: str, lecture_id: str) -> Iterator[Path]:
        draft_dir = self.layout.course_canvas_draft_dir(course_id, lecture_id)
        with locked_course_state(self.layout.course_root(course_id)):
            with locked_canvas_paths(draft_dir):
                yield draft_dir


def initialize_learning_design(
    document: CanvasDocument,
    draft_dir: Path,
    source_revision: str,
) -> LearningDesignReview:
    learning_map = build_learning_map(document)
    review = LearningDesignReview(
        course_id=document.course_id,
        lecture_id=document.lecture_id,
        draft_digest=canvas_digest(document),
        source_revision=source_revision,
        learning_map=learning_map,
        warnings=learning_design_warnings(learning_map),
    )
    review_path(draft_dir).write_text(review.model_dump_json(indent=2), encoding="utf-8")
    return review


def approved_learning_design(
    layout: StorageLayout,
    *,
    draft_dir: Path,
    course_id: str,
    lecture_id: str,
) -> LearningDesignReview:
    current = _current_review(layout, draft_dir, course_id, lecture_id)
    approval = current.approval
    if approval is None or (
        approval.draft_digest != current.draft_digest
        or approval.source_revision != current.source_revision
        or approval.learning_map_revision != current.learning_map.revision
    ):
        raise LearningDesignApprovalRequiredError(
            "Approve the current learning design before publishing this draft."
        )
    return current


def canvas_digest(document: CanvasDocument) -> str:
    payload = document.model_dump(mode="json", exclude={"workspace_path"})
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def learning_design_warnings(learning_map: LearningMap) -> list[str]:
    warnings = [
        f"{node.title} has no assessment."
        for node in learning_map.nodes
        if not node.gate_ids and not node.quiz_ids
    ]
    warnings.extend(
        f"{gate.title} has no unfamiliar transfer task."
        for gate in learning_map.gates
        if not gate.transfer_prompt
    )
    if not learning_map.gates:
        warnings.append("This lecture has no open-answer checkpoint.")
    return warnings


def review_path(draft_dir: Path) -> Path:
    return draft_dir / "learning-design.json"


def _current_review(
    layout: StorageLayout,
    draft_dir: Path,
    course_id: str,
    lecture_id: str,
) -> LearningDesignReview:
    if not (draft_dir / "index.md").exists():
        raise LearningDesignUnavailableError("No canvas draft exists for this lecture.")
    stored = _read_review(review_path(draft_dir))
    if stored is None:
        raise LearningDesignUnavailableError(
            "Regenerate this draft before reviewing its learning design."
        )
    document = read_document_source(draft_dir)
    current_source = lecture_source_revision(layout, course_id=course_id, lecture_id=lecture_id)
    if current_source is None:
        raise LearningDesignUnavailableError(
            "Draft source provenance is unavailable. Regenerate the draft."
        )
    if (
        stored.course_id != course_id
        or stored.lecture_id != lecture_id
        or stored.draft_digest != canvas_digest(document)
        or stored.source_revision != current_source
    ):
        raise LearningDesignStaleError(
            "The draft or its source revision changed. Regenerate and review it again."
        )
    return stored


def _apply_update(current: LearningMap, update: LearningDesignUpdate) -> LearningMap:
    gate_inputs = {gate.id: gate for gate in update.gates}
    node_inputs = {item.section_id: item for item in update.prerequisites}
    current_gate_ids = {gate.id for gate in current.gates}
    current_node_ids = {node.section_id for node in current.nodes}
    if len(gate_inputs) != len(update.gates) or set(gate_inputs) != current_gate_ids:
        raise LearningDesignError("Learning-design gate IDs must match the current draft.")
    if len(node_inputs) != len(update.prerequisites) or set(node_inputs) != current_node_ids:
        raise LearningDesignError("Learning-design section IDs must match the current draft.")
    graph = {section_id: item.prerequisite_ids for section_id, item in node_inputs.items()}
    _validate_prerequisites(graph, current_node_ids)
    payload = current.model_dump(mode="json", exclude={"revision"})
    payload["objective"] = update.objective
    for gate in payload["gates"]:
        changed = gate_inputs[gate["id"]]
        gate.update(
            prompt=changed.prompt,
            evidence_required=" ".join(item.description for item in changed.evidence_criteria),
            evidence_criteria=[item.model_dump(mode="json") for item in changed.evidence_criteria],
            transfer_prompt=changed.transfer_prompt,
            review_after_days=changed.review_after_days,
        )
    for node in payload["nodes"]:
        node["prerequisites"] = graph[node["section_id"]]
    return LearningMap.model_validate(payload)


def _validate_prerequisites(graph: dict[str, list[str]], valid_ids: set[str]) -> None:
    for section_id, prerequisites in graph.items():
        if len(set(prerequisites)) != len(prerequisites):
            raise LearningDesignError("Prerequisites cannot contain duplicates.")
        if section_id in prerequisites:
            raise LearningDesignError("A section cannot be its own prerequisite.")
        if not set(prerequisites) <= valid_ids:
            raise LearningDesignError("Prerequisites must reference current draft sections.")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(section_id: str) -> None:
        if section_id in visiting:
            raise LearningDesignError("Prerequisites must not contain a cycle.")
        if section_id in visited:
            return
        visiting.add(section_id)
        for prerequisite in graph[section_id]:
            visit(prerequisite)
        visiting.remove(section_id)
        visited.add(section_id)

    for section_id in graph:
        visit(section_id)


def _require_request_version(review: LearningDesignReview, digest: str, revision: str) -> None:
    if review.draft_digest != digest or review.source_revision != revision:
        raise LearningDesignStaleError(
            "The draft or its source revision changed. Reload the learning design."
        )


def _read_review(path: Path) -> LearningDesignReview | None:
    if not path.exists():
        return None
    try:
        return LearningDesignReview.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise LearningDesignUnavailableError(
            "Stored learning-design review is invalid. Regenerate the draft."
        ) from exc


def _write_review(path: Path, review: LearningDesignReview) -> None:
    ensure_durable_directory(path.parent)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(review.model_dump_json(indent=2))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)

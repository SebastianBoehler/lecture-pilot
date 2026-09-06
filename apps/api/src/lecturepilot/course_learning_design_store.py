import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from lecturepilot.canvas_markdown import read_document_source
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.canvas_snapshot import locked_canvas_paths
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot import course_practice_design_binding as practice_bindings
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.course_learning_design_errors import (
    LearningDesignError as LearningDesignError,
    LearningDesignStaleError as LearningDesignStaleError,
    LearningDesignUnavailableError as LearningDesignUnavailableError,
    LearningDesignApprovalRequiredError as LearningDesignApprovalRequiredError,
)
from lecturepilot.course_learning_design_models import (
    LearningDesignApproval,
    LearningDesignReview,
    LearningDesignUpdate,
)
from lecturepilot.course_learning_design_update import apply_learning_design_update
from lecturepilot.durable_files import atomic_write_text
from lecturepilot.learning_design_report import build_learning_design_report
from lecturepilot.learning_map import build_learning_map
from lecturepilot.storage_layout import StorageLayout
from lecturepilot.course_update_recovery import locked_course_state


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
            _require_request_version(
                current,
                update.draft_digest,
                update.source_revision,
                update.practice_design_revision,
                update.learning_map_revision,
            )
            try:
                learning_map = apply_learning_design_update(current.learning_map, update)
            except ValueError as exc:
                raise LearningDesignError(str(exc)) from exc
            _bound_design(
                self.layout, draft_dir, learning_map, course_id, lecture_id, current.source_revision
            )
            document = read_document_source(draft_dir)
            report = build_learning_design_report(
                document=document,
                learning_map=learning_map,
                draft_digest=current.draft_digest,
                source_revision=current.source_revision,
            )
            changed = current.model_copy(
                update={
                    "learning_map": learning_map,
                    "report": report,
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
        practice_design_revision: str,
        learning_map_revision: str,
        report_revision: str,
        approved_by: str,
    ) -> LearningDesignReview:
        with self._locked_draft(course_id, lecture_id) as draft_dir:
            current = _current_review(self.layout, draft_dir, course_id, lecture_id)
            _require_request_version(
                current,
                draft_digest,
                source_revision,
                practice_design_revision,
                learning_map_revision,
            )
            _require_report_revision(current, report_revision=report_revision)
            approval = LearningDesignApproval(
                approved_by=approved_by,
                approved_at=datetime.now(UTC),
                draft_digest=current.draft_digest,
                source_revision=current.source_revision,
                practice_design_revision=current.practice_design_revision,
                learning_intent_revision=current.learning_intent_revision,
                learning_map_revision=current.learning_map.revision,
                report_revision=current.report.report_revision,
                acknowledged_warning_ids=[],
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
    practice_design: PracticeDesign,
) -> LearningDesignReview:
    learning_map = build_learning_map(document, practice_design)
    draft_digest = canvas_digest(document)
    report = build_learning_design_report(
        document=document,
        learning_map=learning_map,
        draft_digest=draft_digest,
        source_revision=source_revision,
    )
    review = LearningDesignReview(
        schema_version=2,
        course_id=document.course_id,
        lecture_id=document.lecture_id,
        draft_digest=draft_digest,
        source_revision=source_revision,
        practice_design_revision=practice_design.revision,
        learning_intent_revision=practice_design.learning_intent.revision
        if practice_design.learning_intent
        else None,
        learning_map=learning_map,
        report=report,
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
        or approval.practice_design_revision != current.practice_design_revision
        or approval.learning_intent_revision != current.learning_intent_revision
        or approval.learning_map_revision != current.learning_map.revision
        or approval.report_revision != current.report.report_revision
    ):
        raise LearningDesignApprovalRequiredError(
            "Approve the current learning design before publishing this draft."
        )
    return current


def canvas_digest(document: CanvasDocument) -> str:
    payload = document.model_dump(mode="json", exclude={"workspace_path"})
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
    design = _bound_design(
        layout, draft_dir, stored.learning_map, course_id, lecture_id, current_source
    )
    if (
        stored.course_id != course_id
        or stored.lecture_id != lecture_id
        or stored.draft_digest != canvas_digest(document)
        or stored.source_revision != current_source
        or stored.practice_design_revision != design.revision
        or stored.learning_intent_revision
        != (design.learning_intent.revision if design.learning_intent else None)
        or stored.report.draft_digest != stored.draft_digest
        or stored.report.source_revision != stored.source_revision
        or stored.report.learning_map_revision != stored.learning_map.revision
    ):
        raise LearningDesignStaleError(
            "The draft or its source revision changed. Regenerate and review it again."
        )
    return stored


def _require_request_version(
    review: LearningDesignReview,
    digest: str,
    source_revision: str,
    practice_design_revision: str,
    learning_map_revision: str,
) -> None:
    if (
        review.draft_digest != digest
        or review.source_revision != source_revision
        or review.practice_design_revision != practice_design_revision
        or review.learning_map.revision != learning_map_revision
    ):
        raise LearningDesignStaleError(
            "The draft or its source revision changed. Reload the learning design."
        )


def _require_report_revision(
    review: LearningDesignReview,
    *,
    report_revision: str,
) -> None:
    if report_revision != review.report.report_revision:
        raise LearningDesignStaleError(
            "The learning-design report changed. Reload the current draft before approval."
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


def _bound_design(
    layout: StorageLayout,
    draft_dir: Path,
    learning_map,
    course_id: str,
    lecture_id: str,
    source_revision: str,
) -> PracticeDesign:
    try:
        return practice_bindings.validate_bound_learning_map(
            layout,
            draft_dir,
            learning_map,
            course_id=course_id,
            lecture_id=lecture_id,
            source_revision=source_revision,
        )
    except practice_bindings.PracticeDesignBindingError as exc:
        raise LearningDesignUnavailableError(str(exc)) from exc
    except ValueError as exc:
        raise LearningDesignStaleError(str(exc)) from exc


def _write_review(path: Path, review: LearningDesignReview) -> None:
    atomic_write_text(path, review.model_dump_json(indent=2))

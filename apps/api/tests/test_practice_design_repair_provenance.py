from pathlib import Path

import pytest

from lecturepilot import course_canvas_generation as generation
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_generation_jobs import CanvasGenerationStore
from lecturepilot.course_canvas_generation_ownership import CanvasGenerationOwnershipError
from lecturepilot.course_canvas_generation_service import (
    CANVAS_GENERATION_LEASE_SECONDS,
    run_idempotent_canvas_generation,
)
from lecturepilot.course_practice_design_models import PracticeDesignUpdate
from lecturepilot.course_practice_design_store import PracticeDesignStore
from test_learning_design_review_routes import _document
from test_practice_design_generation_preflight import (
    COURSE_ID,
    LECTURE_ID,
    SOURCE_PATH,
    _app,
    _context,
    _save_design,
    _targeted_failure,
    _write_manifest,
)
from practice_design_test_helpers import passing_review, source_document


@pytest.mark.anyio
async def test_repairable_failure_persists_the_frozen_source_and_design_revisions(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    _write_manifest(app, "a" * 64)
    approved = _save_design(app, approved=True)
    app.state.course_planner = _SourceChangingFailurePlanner(app)
    store = CanvasGenerationStore(
        app.state.canvas_workspace.layout,
        lease_seconds=CANVAS_GENERATION_LEASE_SECONDS,
    )
    request_key = "repair-provenance-failure-0001"

    with pytest.raises(CanvasGenerationRepairableError):
        await run_idempotent_canvas_generation(
            app=app,
            store=store,
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
            actor_user_id=_context().user_id,
            request_key=request_key,
            generate=lambda generation_id, attempt: generation.generate_course_canvas_draft(
                app,
                course_id=COURSE_ID,
                lecture_id=LECTURE_ID,
                context=_context(),
                source_document=lambda _course_id, _lecture_id: _document(),
                generation_id=generation_id,
                attempt=attempt,
            ),
        )

    failed = store.read(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        actor_user_id=_context().user_id,
        request_key=request_key,
    )
    assert failed is not None and failed.repair is not None
    assert failed.repair.source_revision == approved.source_revision
    assert failed.repair.practice_design_revision == approved.revision


@pytest.mark.anyio
async def test_targeted_repair_rejects_a_reapproved_design_before_model_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _app(tmp_path)
    _write_manifest(app, "a" * 64)
    approved = _save_design(app, approved=True)
    failure = _failure_with_revisions(approved.source_revision, approved.revision)
    changed = _replace_and_approve_design(app, approved)
    assert changed.revision != approved.revision
    repair_calls = []

    async def repair_callback(*_args, **_kwargs):
        repair_calls.append(True)
        return _document()

    monkeypatch.setattr(app.state.course_planner, "plan_canvas", repair_callback)

    with pytest.raises(CanvasGenerationOwnershipError, match="practice design changed"):
        await generation.repair_targeted_course_canvas_draft(
            app,
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
            context=_context(),
            source_document=lambda _course_id, _lecture_id: _document(),
            failure=failure,
            generation_id="b" * 32,
            attempt=1,
        )

    assert repair_calls == []
    draft = app.state.canvas_workspace.course_canvas_store.draft_path(COURSE_ID, LECTURE_ID)
    assert not draft.exists()


@pytest.mark.anyio
@pytest.mark.parametrize("missing", ["source_revision", "practice_design_revision"])
async def test_targeted_repair_rejects_legacy_candidates_with_incomplete_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    app = _app(tmp_path)
    _write_manifest(app, "a" * 64)
    approved = _save_design(app, approved=True)
    failure = _failure_with_revisions(approved.source_revision, approved.revision)
    failure = failure.model_copy(
        update={"repair": failure.repair.model_copy(update={missing: None})}
    )
    repair_calls = []
    monkeypatch.setattr(
        app.state.course_planner,
        "plan_canvas",
        lambda *_args, **_kwargs: repair_calls.append(True),
    )

    with pytest.raises(CanvasGenerationRepairableError, match="provenance is unavailable"):
        await generation.repair_targeted_course_canvas_draft(
            app,
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
            context=_context(),
            source_document=lambda _course_id, _lecture_id: _document(),
            failure=failure,
            generation_id="c" * 32,
            attempt=1,
        )

    assert repair_calls == []


class _SourceChangingFailurePlanner:
    def __init__(self, app) -> None:
        self.app = app

    async def plan_canvas(self, _source, *, practice_design, **_kwargs):
        _write_manifest(self.app, "b" * 64)
        raise CanvasGenerationRepairableError(
            "Generated content needs a targeted repair.",
            candidate=_document(),
            section_id="intro",
        )


def _failure_with_revisions(source_revision: str, practice_design_revision: str):
    failure = _targeted_failure()
    return failure.model_copy(
        update={
            "repair": failure.repair.model_copy(
                update={
                    "source_revision": source_revision,
                    "practice_design_revision": practice_design_revision,
                }
            )
        }
    )


def _replace_and_approve_design(app, approved):
    store = PracticeDesignStore(app.state.canvas_workspace.layout)
    changed = store.update(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        current_source_revision=approved.source_revision,
        update=PracticeDesignUpdate(
            source_revision=approved.source_revision,
            practice_design_revision=approved.revision,
            lecture_title=approved.lecture_title,
            objective="Derive a revised conclusion independently from the cited evidence.",
            planning_context=approved.planning_context,
            targets=approved.targets,
        ),
        source=source_document(SOURCE_PATH),
        allowed_source_paths=(SOURCE_PATH,),
    )
    changed = store.save_review(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        source_revision=changed.source_revision,
        design_revision=changed.revision,
        review=passing_review(),
        source=source_document(SOURCE_PATH),
        allowed_source_paths=(SOURCE_PATH,),
        expected_design_review=None,
        expected_design_approval=None,
    )
    return store.approve(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        source_revision=changed.source_revision,
        design_revision=changed.revision,
        approved_by="prof01",
    )

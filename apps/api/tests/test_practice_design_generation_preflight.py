import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from lecturepilot.app import create_app
from lecturepilot.canvas.canvas_models import CanvasDocument
from lecturepilot.canvas.canvas_workspace import CanvasWorkspace
from lecturepilot.authoring.course_canvas_generation import (
    generate_course_canvas_draft,
    repair_targeted_course_canvas_draft,
)
from lecturepilot.authoring.course_canvas_generation_jobs import CanvasGenerationJob
from lecturepilot.authoring.course_canvas_repair_target import CanvasGenerationRepairTarget
from lecturepilot.authoring.course_canvas_repairs import lecture_source_revision
from lecturepilot.canvas.course_canvas_store import InvalidCanvasDraftError
from lecturepilot.learning_design.course_practice_design_store import (
    PracticeDesignApprovalRequired,
    PracticeDesignStale,
    PracticeDesignStore,
)
from lecturepilot.identity.tenancy import TenantContext, TenantRole
from approved_practice_design_helpers import approved_practice_design, revised_design, store_design
from practice_design_test_helpers import proposal
from test_learning_design_review_routes import _document


COURSE_ID = "design-course"
LECTURE_ID = "lecture-01"
SOURCE_PATH = "lecture-01.md"


@pytest.mark.anyio
@pytest.mark.parametrize("state", ["missing", "unapproved", "stale"])
async def test_generation_rejects_noncurrent_design_before_model_invocation(
    tmp_path: Path, state: str
) -> None:
    app = _app(tmp_path)
    _write_manifest(app, "a" * 64)
    design = _save_design(app, approved=state != "unapproved") if state != "missing" else None
    if state == "stale":
        assert design is not None
        _write_manifest(app, "b" * 64)
    planner = _Planner()
    app.state.course_planner = planner

    error = PracticeDesignStale if state == "stale" else PracticeDesignApprovalRequired
    with pytest.raises(error):
        await _generate(app)

    assert planner.calls == []


@pytest.mark.anyio
async def test_generation_persists_only_while_frozen_design_is_current(tmp_path: Path) -> None:
    app = _app(tmp_path)
    _write_manifest(app, "a" * 64)
    approved = _save_design(app, approved=True)
    store = PracticeDesignStore(app.state.canvas_workspace.layout)
    planner = _Planner(
        on_plan=lambda: _edit_design(store, approved, app),
    )
    app.state.course_planner = planner

    with pytest.raises(InvalidCanvasDraftError, match="practice design changed"):
        await _generate(app)

    assert planner.calls == [approved]
    assert not app.state.canvas_workspace.course_canvas_store.draft_path(
        COURSE_ID, LECTURE_ID
    ).exists()


@pytest.mark.anyio
async def test_targeted_repair_receives_frozen_design_and_rejects_edit_before_persisting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _app(tmp_path)
    _write_manifest(app, "a" * 64)
    approved = _save_design(app, approved=True)
    store = PracticeDesignStore(app.state.canvas_workspace.layout)
    received = []

    async def repair_callback(_source, *, practice_design, **_kwargs):
        received.append(practice_design)
        _edit_design(store, approved, app)
        return failure.repair.candidate

    monkeypatch.setattr(app.state.course_planner, "plan_canvas", repair_callback)
    failure = _targeted_failure()
    failure = failure.model_copy(
        update={
            "repair": failure.repair.model_copy(
                update={
                    "source_revision": approved.source_revision,
                    "practice_design_revision": approved.revision,
                }
            )
        }
    )

    with pytest.raises(InvalidCanvasDraftError, match="practice design changed"):
        await repair_targeted_course_canvas_draft(
            app,
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
            context=_context(),
            source_document=lambda _course_id, _lecture_id: _document(),
            failure=failure,
            generation_id="b" * 32,
            attempt=1,
        )

    assert received == [approved]
    assert not app.state.canvas_workspace.course_canvas_store.draft_path(
        COURSE_ID, LECTURE_ID
    ).exists()


class _Planner:
    def __init__(self, on_plan=None) -> None:
        self.calls = []
        self.on_plan = on_plan

    async def plan_canvas(self, source, *, practice_design, **_kwargs):
        self.calls.append(practice_design)
        if self.on_plan:
            self.on_plan()
        return source


def _app(tmp_path: Path):
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    return app


def _save_design(app, *, approved: bool):
    revision = lecture_source_revision(
        app.state.canvas_workspace.layout, course_id=COURSE_ID, lecture_id=LECTURE_ID
    )
    assert revision is not None
    return store_design(
        app.state.canvas_workspace.layout,
        approved_practice_design(
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
            source_revision=revision,
            targets=proposal().targets,
            approved=approved,
        ),
    )


def _edit_design(store: PracticeDesignStore, design, app) -> None:
    store_design(
        store.layout,
        revised_design(design, objective="Derive a revised conclusion from the cited evidence."),
    )


async def _generate(app) -> CanvasDocument:
    return await generate_course_canvas_draft(
        app,
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        context=_context(),
        source_document=lambda _course_id, _lecture_id: _document(),
        generation_id="a" * 32,
        attempt=1,
    )


def _targeted_failure() -> CanvasGenerationJob:
    now = datetime.now(UTC)
    return CanvasGenerationJob(
        generation_id="c" * 32,
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        actor_key="a" * 24,
        request_key_hash="a" * 64,
        status="failed",
        attempt=1,
        created_at=now,
        updated_at=now,
        error_code="canvas_generation_repairable_error",
        error_detail="Canvas quality review failed.",
        repair=CanvasGenerationRepairTarget(
            candidate=_document(),
            section_id="intro",
            source_revision="a" * 64,
        ),
    )


def _write_manifest(app, sha256: str) -> None:
    path = app.state.canvas_workspace.layout.lecture_source_manifest_path(COURSE_ID, LECTURE_ID)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "course_id": COURSE_ID,
                "lecture_id": LECTURE_ID,
                "files": [{"path": SOURCE_PATH, "sha256": sha256}],
            }
        ),
        encoding="utf-8",
    )


def _context() -> TenantContext:
    return TenantContext(
        tenant_id="tenant-tuebingen",
        user_id="prof01",
        roles=frozenset({TenantRole.PROFESSOR}),
        course_ids=frozenset(),
        auth_mode="dev",
    )

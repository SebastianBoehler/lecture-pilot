import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from lecturepilot import course_canvas_draft_routes
from lecturepilot import course_canvas_generation as generation
from lecturepilot import course_canvas_repair_routes
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_canvas_generation_ownership import CanvasGenerationOwnershipError
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.course_practice_design_store import PracticeDesignStore
from lecturepilot.providers import ProviderRegistry
from practice_design_test_helpers import proposal
from test_learning_design_review_routes import _document


COURSE_ID = "design-course"
LECTURE_ID = "lecture-01"
SOURCE_PATH = "lecture-01.md"


@pytest.mark.anyio
async def test_real_planner_accepts_frozen_practice_design(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, design = _approved_app(tmp_path, "a" * 64)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    document = _document()
    target = design.targets[0]
    section = document.sections[0]
    document = document.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={
                        "blocks": [
                            *section.blocks,
                            CanvasBlock(
                                id=f"practice-{target.id}",
                                type="checkpoint",
                                text=target.baseline_task,
                            ),
                        ]
                    }
                )
            ]
        }
    )

    async def plan_sections(**_kwargs):
        return document

    planner = CourseCanvasPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        quality_reviewer=_NoQualityReviewer(),
    )
    monkeypatch.setattr(
        "lecturepilot.course_canvas_planner.plan_sections_individually", plan_sections
    )
    monkeypatch.setattr(
        "lecturepilot.course_canvas_planner.validate_planned_document", lambda *_args: None
    )

    document = await planner.plan_canvas(document, practice_design=design)

    assert document.title == "Learning design"
    assert app.state.canvas_workspace.layout.course_root(COURSE_ID).exists()


@pytest.mark.anyio
async def test_targeted_repair_rejects_candidate_after_snapshot_source_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, approved = _approved_app(tmp_path, "a" * 64)
    failure = _failure(approved.source_revision)
    _write_manifest(app, "b" * 64)
    _replace_approved_design(app, approved)
    callback_calls = []

    async def repair_callback(*_args, **_kwargs):
        callback_calls.append(True)
        return _document()

    monkeypatch.setattr(generation, "repair_until_quality_valid", repair_callback)

    with pytest.raises(CanvasGenerationOwnershipError, match="source changed after this failure"):
        await generation.repair_targeted_course_canvas_draft(
            app,
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
            context=SimpleNamespace(user_id="prof01"),
            source_document=lambda _course_id, _lecture_id: _document(),
            failure=failure,
            generation_id="b" * 32,
            attempt=1,
        )

    assert callback_calls == []


@pytest.mark.parametrize("route_module", [course_canvas_draft_routes, course_canvas_repair_routes])
def test_corrupt_practice_design_is_a_preflight_conflict(tmp_path: Path, route_module) -> None:
    app, _ = _approved_app(tmp_path, "a" * 64)
    path = app.state.canvas_workspace.layout.lecture_practice_design_path(COURSE_ID, LECTURE_ID)
    path.write_text("not json", encoding="utf-8")

    with pytest.raises(HTTPException) as error:
        route_module._require_current_practice_design(
            app, COURSE_ID, LECTURE_ID, lambda _course_id, _lecture_id: _document()
        )

    assert error.value.status_code == 409


class _NoQualityReviewer:
    async def review(self, **_kwargs):
        return []


def _approved_app(tmp_path: Path, sha256: str):
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    _write_manifest(app, sha256)
    return app, _save_design(app, expected=None)


def _replace_approved_design(app, previous):
    return _save_design(app, expected=previous)


def _save_design(app, *, expected):
    store = PracticeDesignStore(app.state.canvas_workspace.layout)
    revision = generation.lecture_source_revision(
        app.state.canvas_workspace.layout, course_id=COURSE_ID, lecture_id=LECTURE_ID
    )
    assert revision is not None
    design = store.save_proposal(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        source_revision=revision,
        proposal=proposal(),
        allowed_source_paths=(SOURCE_PATH,),
        expected_design_revision=expected.revision if expected else None,
        expected_design_approval=expected.approval if expected else None,
    )
    return store.approve(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        source_revision=revision,
        design_revision=design.revision,
        approved_by="prof01",
    )


def _failure(source_revision: str):
    from test_practice_design_generation_preflight import _targeted_failure

    failure = _targeted_failure()
    return failure.model_copy(
        update={"repair": failure.repair.model_copy(update={"source_revision": source_revision})}
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

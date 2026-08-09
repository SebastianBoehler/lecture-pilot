import json
import asyncio
from pathlib import Path

import pytest

from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_canvas_generation import generate_course_canvas_draft
from lecturepilot.course_canvas_store import InvalidCanvasDraftError
from lecturepilot.tenancy import TenantContext, TenantRole

from test_learning_design_review_routes import _document


@pytest.mark.anyio
async def test_generation_rejects_source_revision_that_changes_during_planning(
    tmp_path: Path,
) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    manifest = app.state.canvas_workspace.layout.lecture_source_manifest_path(
        "design-course", "lecture-01"
    )
    _write_manifest(manifest, "a" * 64)
    app.state.course_planner = _SourceChangingPlanner(manifest)

    with pytest.raises(
        InvalidCanvasDraftError,
        match="Course sources changed during generation",
    ):
        await generate_course_canvas_draft(
            app,
            course_id="design-course",
            lecture_id="lecture-01",
            context=TenantContext(
                tenant_id="tenant-tuebingen",
                user_id="prof01",
                roles=frozenset({TenantRole.PROFESSOR}),
                course_ids=frozenset(),
                auth_mode="dev",
            ),
            source_document=lambda _course_id, _lecture_id: _document(),
            generation_id="a" * 32,
            attempt=1,
        )

    assert not app.state.canvas_workspace.course_canvas_store.draft_path(
        "design-course", "lecture-01"
    ).exists()


@pytest.mark.anyio
async def test_newer_generation_owns_the_draft_when_older_planning_finishes_last(
    tmp_path: Path,
) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    manifest = app.state.canvas_workspace.layout.lecture_source_manifest_path(
        "design-course", "lecture-01"
    )
    _write_manifest(manifest, "a" * 64)
    planner = _InterleavedPlanner()
    app.state.course_planner = planner
    source_titles = iter(("Older generation", "Newer generation"))

    older = asyncio.create_task(
        generate_course_canvas_draft(
            app,
            course_id="design-course",
            lecture_id="lecture-01",
            context=_context(),
            source_document=lambda _course_id, _lecture_id: _document(title=next(source_titles)),
            generation_id="a" * 32,
            attempt=1,
        )
    )
    await planner.older_planning.wait()
    newer = await generate_course_canvas_draft(
        app,
        course_id="design-course",
        lecture_id="lecture-01",
        context=_context(),
        source_document=lambda _course_id, _lecture_id: _document(title=next(source_titles)),
        generation_id="b" * 32,
        attempt=1,
    )
    planner.release_older.set()

    with pytest.raises(InvalidCanvasDraftError, match="superseded"):
        await older

    stored = app.state.canvas_workspace.read_course_canvas_draft(
        course_id="design-course", lecture_id="lecture-01"
    )
    assert newer.title == "Newer generation"
    assert stored.title == "Newer generation"
    ownership = json.loads(
        (
            app.state.canvas_workspace.layout.course_root("design-course")
            / "builder"
            / "generation-ownership"
            / "lecture-01.json"
        ).read_text(encoding="utf-8")
    )
    assert ownership["generation_id"] == "b" * 32
    assert ownership["attempt"] == 1
    assert ownership["sequence"] == 2
    assert not (
        app.state.canvas_workspace.course_canvas_store.draft_path("design-course", "lecture-01")
        / "generation-owner.json"
    ).exists()


class _SourceChangingPlanner:
    def __init__(self, manifest: Path) -> None:
        self.manifest = manifest

    async def plan_canvas(self, source, **_kwargs):
        _write_manifest(self.manifest, "b" * 64)
        return source


class _InterleavedPlanner:
    def __init__(self) -> None:
        self.older_planning = asyncio.Event()
        self.release_older = asyncio.Event()

    async def plan_canvas(self, source, **_kwargs):
        if source.title == "Older generation":
            self.older_planning.set()
            await self.release_older.wait()
        return source


def _context() -> TenantContext:
    return TenantContext(
        tenant_id="tenant-tuebingen",
        user_id="prof01",
        roles=frozenset({TenantRole.PROFESSOR}),
        course_ids=frozenset(),
        auth_mode="dev",
    )


def _write_manifest(path: Path, sha256: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "course_id": "design-course",
                "lecture_id": "lecture-01",
                "files": [{"path": "lecture.md", "sha256": sha256}],
            }
        ),
        encoding="utf-8",
    )

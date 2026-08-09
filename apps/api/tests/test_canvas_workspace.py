from pathlib import Path

import pytest

from canvas_workspace_fixtures import course_canvas, publish_course_canvas
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace, CanvasWorkspaceError
from lecturepilot.models import CanvasSectionPlacement


def test_published_canvas_reads_do_not_materialize_learner_copies(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    learner_root = workspace.layout.user_lecture_root("alice", "martius-ml", "lecture-03")

    document = workspace.read_document(
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="alice",
    )

    assert [section.id for section in document.sections] == ["bayes-formula"]
    assert not (learner_root / "canvas").exists()
    assert not (learner_root / "canvas.json").exists()
    assert document.workspace_path == str(
        workspace.layout.course_canvas_dir("martius-ml", "lecture-03") / "index.md"
    )


def test_current_markdown_sections_are_isolated_and_persisted(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    section = _student_section("student-soccer", "A student-specific transfer example.")

    alice = workspace.apply_sections(
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="alice",
        sections=[section],
    )
    bob = workspace.read_document(
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="bob",
    )

    assert any(item.id == section.id for item in alice.sections)
    assert all(item.id != section.id for item in bob.sections)
    path = (
        workspace.layout.user_canvas_dir("alice", "martius-ml", "lecture-03")
        / "student"
        / "90-student-soccer.md"
    )
    assert path.exists()


def test_student_section_placement_survives_reload(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    first = _student_section("student-posterior", "Posterior note.")
    second = _student_section("student-risk", "Risk note.")

    workspace.apply_sections(
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="alice",
        sections=[first, second],
        placements={
            first.id: CanvasSectionPlacement(section_id="bayes-formula"),
            second.id: CanvasSectionPlacement(section_id="bayes-formula"),
        },
    )
    reloaded = workspace.read_document(
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="alice",
    )

    assert [section.id for section in reloaded.sections] == [
        "bayes-formula",
        first.id,
        second.id,
    ]


def test_student_asset_logical_path_resolves_from_current_canvas(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    canvas_dir = workspace.layout.user_canvas_dir("alice", "martius-ml", "lecture-03")
    asset = canvas_dir / "student-assets" / "regression.jpg"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"jpg")
    section = CanvasSection(
        id="student-visual",
        title="Visual",
        source_ref="student workspace",
        blocks=[
            CanvasBlock(
                id="student-visual-asset",
                type="asset",
                asset_path="student-assets/regression.jpg",
            )
        ],
    )

    document = workspace.apply_sections(
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="alice",
        sections=[section],
    )

    block = next(item for item in document.sections if item.id == section.id).blocks[0]
    assert block.asset_url is not None
    assert block.asset_url.startswith("/workspace-assets/martius-ml/lecture-03/")


def test_real_republish_replaces_official_markdown_and_keeps_learner_markdown(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    workspace.apply_sections(
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="alice",
        sections=[_student_section("student-note", "Personal note.")],
    )
    publish_course_canvas(workspace, course_canvas("losses", "Losses"))

    refreshed = workspace.read_document(
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="alice",
    )

    assert {section.id for section in refreshed.sections} == {"losses", "student-note"}


@pytest.mark.parametrize("asset_path", ["../secret.png", "/tmp/image.png", "notes.pdf"])
def test_asset_paths_stay_inside_browser_image_allowlist(tmp_path: Path, asset_path: str) -> None:
    workspace = _workspace(tmp_path)

    with pytest.raises(CanvasWorkspaceError):
        workspace.asset_path(
            course_id="martius-ml",
            lecture_id="lecture-03",
            asset_path=asset_path,
        )


def _workspace(tmp_path: Path) -> CanvasWorkspace:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    publish_course_canvas(workspace, course_canvas("bayes-formula", "Bayes formula"))
    return workspace


def _student_section(section_id: str, text: str) -> CanvasSection:
    return CanvasSection(
        id=section_id,
        title="Learner section",
        source_ref="student workspace",
        blocks=[CanvasBlock(id=f"{section_id}-p", type="paragraph", text=text)],
    )

from pathlib import Path

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace, CanvasWorkspaceError
from lecturepilot.latex_canvas_importer import CANVAS_IMPORT_VERSION
from canvas_workspace_fixtures import course_canvas, write_course_source


def test_imports_latex_canvas_into_pseudonymous_student_workspace(tmp_path: Path) -> None:
    material_root = write_course_source(tmp_path)
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )

    document = workspace.read_document(
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="student01",
    )

    assert document.title == "Bayesian Decision Theory"
    assert [section.id for section in document.sections] == [
        "bayesian-decision-theory-the-aim",
        "bayes-formula",
        "bayes-rule-to-sum-up",
        "naive-bayes-classifiers",
        "losses-and-risks",
    ]
    assert any(
        block.asset_url == "/course-assets/martius-ml/lecture-03/Ch3/spam-DALL-E.jpg"
        for block in document.sections[0].blocks
    )
    assert any(block.type == "math" for block in document.sections[1].blocks)
    assert "student01" not in document.workspace_path
    assert Path(document.workspace_path).exists()
    assert Path(document.workspace_path).name == "index.md"
    assert "users" in Path(document.workspace_path).parts
    assert "students" not in Path(document.workspace_path).parts
    canvas_dir = Path(document.workspace_path).parent
    assert (canvas_dir / "sections" / "02-bayes-formula.md").exists()
    assert (canvas_dir.parent / "canvas.json").exists()


def test_reads_canvas_from_markdown_section_directory(tmp_path: Path) -> None:
    material_root = write_course_source(tmp_path)
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )
    document = workspace.read_document(
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="student01",
    )
    section_path = Path(document.workspace_path).parent / "sections" / "02-bayes-formula.md"
    section_path.write_text(
        section_path.read_text(encoding="utf-8")
        + '\n\n<!-- block id="bayes-formula-p-extra" type="paragraph" -->\n'
        + "This handwritten Markdown addition should appear in the canvas.\n",
        encoding="utf-8",
    )

    updated = workspace.read_document(
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="student01",
    )

    assert any(
        block.id == "bayes-formula-p-extra"
        and block.text == "This handwritten Markdown addition should appear in the canvas."
        for section in updated.sections
        if section.id == "bayes-formula"
        for block in section.blocks
    )


def test_student_canvas_sections_are_isolated(tmp_path: Path) -> None:
    material_root = write_course_source(tmp_path)
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )
    section = CanvasSection(
        id="student-soccer-bayes-example",
        title="Soccer scouting example",
        blocks=[
            CanvasBlock(
                id="student-soccer-bayes-example-p-1",
                type="paragraph",
                text="A student-specific transfer example.",
            )
        ],
    )

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
    alice_canvas_dir = Path(alice.workspace_path).parent
    student_section = alice_canvas_dir / "student" / "90-student-soccer-bayes-example.md"
    assert student_section.exists()
    assert "A student-specific transfer example." in student_section.read_text(encoding="utf-8")


def test_migrates_existing_compiled_student_sections_to_overlay(tmp_path: Path) -> None:
    material_root = write_course_source(tmp_path)
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )
    compiled_path = workspace.layout.legacy_compiled_canvas_path("alice", "martius-ml", "lecture-03")
    compiled_path.parent.mkdir(parents=True)
    compiled_path.write_text(
        CanvasDocument(
            id="martius-ml-lecture-03",
            import_version=2,
            course_id="martius-ml",
            lecture_id="lecture-03",
            title="Bayesian Decision Theory",
            source_kind="latex",
            source_ref="Lecture03-eng.tex",
            workspace_path=str(compiled_path),
            sections=[
                CanvasSection(
                    id="bayes-formula",
                    title="Bayes formula",
                    source_ref="frames 6, 7, 8, 9",
                    blocks=[CanvasBlock(id="bayes-formula-p-1", type="paragraph", text="Official.")],
                ),
                CanvasSection(
                    id="student-soccer-bayes-example",
                    title="Soccer scouting example",
                    source_ref="student workspace",
                    blocks=[
                        CanvasBlock(
                            id="student-soccer-bayes-example-p-1",
                            type="paragraph",
                            text="Student overlay.",
                        )
                    ],
                ),
            ],
        ).model_dump_json(),
        encoding="utf-8",
    )

    document = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="alice")

    canvas_dir = Path(document.workspace_path).parent
    assert next((canvas_dir / "sections").glob("*-bayes-formula.md"), None) is not None
    assert not (canvas_dir / "sections" / "02-student-soccer-bayes-example.md").exists()
    assert (canvas_dir / "student" / "90-student-soccer-bayes-example.md").exists()


def test_refreshes_stale_markdown_canvas_and_keeps_student_overlay(tmp_path: Path) -> None:
    material_root = write_course_source(tmp_path)
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )
    document = workspace.apply_sections(
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="alice",
        sections=[
            CanvasSection(
                id="student-transfer-example",
                title="Student transfer example",
                source_ref="student workspace",
                blocks=[CanvasBlock(id="student-transfer-example-p-1", type="paragraph", text="Personal note.")],
            )
        ],
    )
    canvas_dir = Path(document.workspace_path).parent
    manifest_path = canvas_dir / "index.md"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace(
            f"import_version: {CANVAS_IMPORT_VERSION}", "import_version: 1"
        ),
        encoding="utf-8",
    )
    stale_section = canvas_dir / "sections" / "04-naive-bayes-classifiers.md"
    stale_section.write_text(stale_section.read_text(encoding="utf-8") + "\nRaw stale official text.\n")

    refreshed = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="alice")
    naive_section = next(section for section in refreshed.sections if section.id == "naive-bayes-classifiers")
    naive_items = [item for block in naive_section.blocks if block.type == "list" for item in block.items]

    assert refreshed.import_version == CANVAS_IMPORT_VERSION
    assert "Raw stale official text." not in stale_section.read_text(encoding="utf-8")
    assert any("likelihood term" in item for item in naive_items)
    assert all(r"\[" not in item and r"\]" not in item for item in naive_items)
    assert all(r"\\" not in item for item in naive_items)
    assert any(section.id == "student-transfer-example" for section in refreshed.sections)


def test_refreshes_user_canvas_when_course_base_changes(tmp_path: Path) -> None:
    material_root = write_course_source(tmp_path)
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )
    workspace.write_course_canvas(course_canvas("old-course-section", "Old course section"))
    workspace.apply_sections(
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="alice",
        sections=[
            CanvasSection(
                id="student-transfer-example",
                title="Student transfer example",
                source_ref="student workspace",
                blocks=[CanvasBlock(id="student-transfer-example-p-1", type="paragraph", text="Personal note.")],
            )
        ],
    )

    workspace.write_course_canvas(course_canvas("new-course-section", "New course section"))
    refreshed = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="alice")

    section_ids = {section.id for section in refreshed.sections}
    assert "new-course-section" in section_ids
    assert "old-course-section" not in section_ids
    assert "student-transfer-example" in section_ids


@pytest.mark.parametrize("asset_path", ["../secret.png", "/tmp/image.png", "notes.pdf"])
def test_asset_paths_stay_inside_browser_image_allowlist(tmp_path: Path, asset_path: str) -> None:
    material_root = write_course_source(tmp_path)
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )

    with pytest.raises(CanvasWorkspaceError):
        workspace.asset_path(
            course_id="martius-ml",
            lecture_id="lecture-03",
            asset_path=asset_path,
        )

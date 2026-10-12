import pytest

from lecturepilot.sources.source_warnings import compact_source_warnings


def page(number, unit="page"):
    return f"OCR required but unavailable for {unit} {number}; the page image was preserved."


def test_page_gaps_collapse_into_one_ranged_line():
    warnings = [page(n) for n in (9, 3, 4, 5, 10, 7, 4)]
    assert compact_source_warnings(warnings) == [
        "OCR required but unavailable for 6 pages (3–5, 7, 9–10); "
        "the page images were preserved and text on them was not extracted."
    ]


def test_single_gap_uses_singular_and_slides_stay_separate():
    compact = compact_source_warnings([page(2, "slide"), page(11)])
    assert compact == [
        "OCR required but unavailable for 1 page (11); "
        "the page images were preserved and text on them was not extracted.",
        "OCR required but unavailable for 1 slide (2); "
        "the slide images were preserved and text on them was not extracted.",
    ]


def test_other_warnings_survive_the_limit_after_many_ocr_pages():
    others = [f"Note {n}" for n in range(25)]
    compact = compact_source_warnings([page(n) for n in range(1, 41)] + others)
    assert len(compact) == 20
    assert compact[0].startswith("OCR required but unavailable for 40 pages (1–40)")
    assert compact[1:] == others[:19]


@pytest.mark.parametrize("warnings", [[], ["LaTeX preview unavailable."], ["OCR required soon"]])
def test_non_ocr_warnings_pass_through_unchanged(warnings):
    assert compact_source_warnings(warnings) == warnings


def test_draft_save_compacts_an_overflowing_warning_list(tmp_path):
    from lecturepilot.canvas.canvas_workspace import CanvasWorkspace
    from test_practice_design_canvas_binding import _approved_design, _document

    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    design = _approved_design(workspace)
    document = _document(design).model_copy(
        update={"warnings": [page(n) for n in range(1, 21)] + ["Quality review left 1 open note."]}
    )
    saved = workspace.write_course_canvas_draft(
        document, expected_source_revision=design.source_revision, practice_design=design
    )
    assert saved.warnings == [
        "OCR required but unavailable for 20 pages (1–20); "
        "the page images were preserved and text on them was not extracted.",
        "Quality review left 1 open note.",
    ]

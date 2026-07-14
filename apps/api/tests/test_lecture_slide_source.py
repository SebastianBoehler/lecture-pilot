from lecturepilot.lecture_slide_source import resolve_lecture_slide_source
from lecturepilot.source_bundle import SourceBundleFile


def test_exact_companion_pdf_is_authoritative() -> None:
    source = resolve_lecture_slide_source(
        files=[
            _file("Lecture02.tex", "latex"),
            _file("Lecture02.pdf", "pdf"),
            _file("Lecture02-handout.pdf", "pdf"),
        ],
        material_path="Lecture02.tex",
        lecture_id="lecture-02",
    )

    assert source.primary_tex_path == "Lecture02.tex"
    assert source.uploaded_pdf_path == "Lecture02.pdf"


def test_numbered_handout_prevents_tex_compilation() -> None:
    source = resolve_lecture_slide_source(
        files=[
            _file("Lecture02.tex", "latex"),
            _file("Lecture01-handout.pdf", "pdf"),
            _file("Lecture02-handout.pdf", "pdf"),
            _file("course-syllabus.pdf", "pdf"),
        ],
        material_path="Lecture02.tex",
        lecture_id="lecture-02",
    )

    assert source.uploaded_pdf_path == "Lecture02-handout.pdf"


def test_unique_lecture_folder_pdf_matches_generic_slide_filename() -> None:
    source = resolve_lecture_slide_source(
        files=[
            _file("Lecture 2/slides.tex", "latex"),
            _file("Lecture 2/handout.pdf", "pdf"),
            _file("Lecture 2/images/example.pdf", "pdf"),
        ],
        material_path="Lecture 2/slides.tex",
        lecture_id="lecture-02",
    )

    assert source.uploaded_pdf_path == "Lecture 2/handout.pdf"


def test_support_tex_is_never_selected_as_primary() -> None:
    source = resolve_lecture_slide_source(
        files=[
            _file("Lecture02.tex", "latex"),
            _file("header.tex", "latex"),
            _file("macros.tex", "latex"),
        ],
        material_path="Lecture02.tex",
        lecture_id="lecture-02",
    )

    assert source.primary_tex_path == "Lecture02.tex"
    assert source.uploaded_pdf_path is None


def test_numbered_figure_pdf_is_not_treated_as_a_slide_deck() -> None:
    source = resolve_lecture_slide_source(
        files=[
            _file("Lecture02.tex", "latex"),
            _file("images/Lecture02-regression-figure.pdf", "pdf"),
        ],
        material_path="Lecture02.tex",
        lecture_id="lecture-02",
    )

    assert source.uploaded_pdf_path is None


def test_explicitly_assigned_generic_pdf_is_authoritative() -> None:
    source = resolve_lecture_slide_source(
        files=[
            _file("Lecture02.tex", "latex"),
            _file("week-two.pdf", "pdf"),
        ],
        material_path="Lecture02.tex",
        lecture_id="lecture-02",
        preferred_pdf_paths={"week-two.pdf"},
    )

    assert source.uploaded_pdf_path == "week-two.pdf"


def test_ambiguous_explicit_pdfs_do_not_suppress_compilation() -> None:
    source = resolve_lecture_slide_source(
        files=[
            _file("Lecture02.tex", "latex"),
            _file("appendix.pdf", "pdf"),
            _file("exercises.pdf", "pdf"),
        ],
        material_path="Lecture02.tex",
        lecture_id="lecture-02",
        preferred_pdf_paths={"appendix.pdf", "exercises.pdf"},
    )

    assert source.uploaded_pdf_path is None


def test_numbered_pdf_from_another_folder_is_not_selected() -> None:
    source = resolve_lecture_slide_source(
        files=[
            _file("lectures/week-02/slides.tex", "latex"),
            _file("archive/Lecture02-handout.pdf", "pdf"),
        ],
        material_path="lectures/week-02/slides.tex",
        lecture_id="lecture-02",
    )

    assert source.uploaded_pdf_path is None


def _file(path: str, kind: str) -> SourceBundleFile:
    return SourceBundleFile(path=path, kind=kind, size_bytes=1)

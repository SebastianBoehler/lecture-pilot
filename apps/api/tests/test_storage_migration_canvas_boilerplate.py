from pathlib import Path

from lecturepilot.canvas_markdown import read_document_source, write_document_source
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.storage_layout import StorageLayout
from lecturepilot.storage_migration_canvas_boilerplate import migrate


TITLE = "Measuring Binary Classifier Performance"
ANCHOR = "In binary classification, we categorize outcomes into four cases: True Positives (TP),"
LEGACY_WHY = (
    f"**Why this matters.** {TITLE} turns the source material into a decision step. "
    f"The key cue is {ANCHOR}. Use it to identify the quantity being estimated, state what "
    "evidence changes it, and connect the result to the decision the learner must make."
)
LEGACY_ITEMS = [
    "Name the source variable or formula before interpreting it.",
    "Explain which part comes from evidence and which part is a modeling choice.",
    "Check how the conclusion would change under a different cost or observation.",
]
LEGACY_CHECK = (
    f"Learning checkpoint: use {ANCHOR} to rephrase the section without slide wording. "
    "A good answer should include the mechanism, a concrete example, and one limitation or "
    "failure mode."
)
CLEAN_WHY = (
    f"**Why this matters.** {TITLE} is useful when the concept changes a decision, estimate, "
    f"or model comparison. Focus on {ANCHOR}. Ask what quantity or case is being estimated, "
    "what evidence changes it, and what action would change if the answer changed."
)
CLEAN_ITEMS = [
    "Identify the relevant variable, formula, metric, or case before interpreting it.",
    "Separate what is observed in the data from what is chosen by the modeler.",
    "Describe how the conclusion would change under a different threshold, cost, or observation.",
]
CLEAN_CHECK = (
    f"Check yourself: In **{TITLE}**, what would you compute or compare first, and why? "
    "Answer with one concrete example from this section and one limitation or failure mode."
)


def _document(canvas_dir: Path) -> CanvasDocument:
    return CanvasDocument(
        id="course-1-lecture-02",
        course_id="course-1",
        lecture_id="lecture-02",
        title="Generalization",
        source_kind="generated",
        source_ref="test",
        workspace_path=str(canvas_dir / "index.md"),
        sections=[
            CanvasSection(
                id="metrics",
                title=TITLE,
                source_ref="frames 18-21",
                blocks=[
                    CanvasBlock(id="intro", type="paragraph", text="Keep this paragraph."),
                    CanvasBlock(id="why", type="paragraph", text=LEGACY_WHY),
                    CanvasBlock(id="study", type="list", items=LEGACY_ITEMS),
                    CanvasBlock(id="check", type="callout", text=LEGACY_CHECK),
                ],
            ),
            CanvasSection(
                id="other",
                title="Other",
                blocks=[CanvasBlock(id="plain", type="paragraph", text="Unrelated.")],
            ),
        ],
    )


def _seed(tmp_path: Path) -> tuple[Path, Path]:
    layout = StorageLayout(tmp_path)
    draft = layout.course_canvas_draft_dir("course-1", "lecture-02")
    published = layout.course_canvas_dir("course-1", "lecture-02")
    for canvas_dir in (draft, published):
        write_document_source(_document(canvas_dir), canvas_dir)
    return draft, published


def test_dry_run_reports_legacy_sections_without_writing(tmp_path: Path) -> None:
    draft, published = _seed(tmp_path)
    before = (draft / "sections" / "01-metrics.md").read_bytes()

    report = migrate(tmp_path, apply=False)

    assert report["applied"] is False
    assert report["canvases_scanned"] == 2
    assert sorted(report["changed_files"]) == sorted(
        str(path.relative_to(tmp_path) / "sections" / "01-metrics.md")
        for path in (draft, published)
    )
    assert report["unmatched_files"] == []
    assert (draft / "sections" / "01-metrics.md").read_bytes() == before


def test_apply_rewrites_only_legacy_blocks_and_is_idempotent(tmp_path: Path) -> None:
    draft, published = _seed(tmp_path)
    other_before = (draft / "sections" / "02-other.md").read_bytes()

    migrate(tmp_path, apply=True)

    for canvas_dir in (draft, published):
        intro, why, study, check = read_document_source(canvas_dir).sections[0].blocks
        assert intro.text == "Keep this paragraph."
        assert why.text == CLEAN_WHY
        assert study.items == CLEAN_ITEMS
        assert check.text == CLEAN_CHECK
    assert (draft / "sections" / "02-other.md").read_bytes() == other_before
    again = migrate(tmp_path, apply=True)
    assert again["changed_files"] == []

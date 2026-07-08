from pathlib import Path

from lecturepilot.canvas_learning_support import (
    normalize_learning_support,
    support_check_prompt,
    support_study_items,
    support_why_text,
)
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_store import CourseCanvasStore
from lecturepilot.storage_layout import StorageLayout


def test_normalizes_legacy_learning_support_copy() -> None:
    anchor = "In binary classification, we categorize outcomes into four cases: True Positives (TP),"
    document = _document(
        [
            CanvasBlock(
                id="metrics-study-support-1",
                type="paragraph",
                text=(
                    "**Why this matters.** Measuring Binary Classifier Performance turns the source "
                    f"material into a decision step. The key cue is {anchor}. Use it to identify the "
                    "quantity being estimated, state what evidence changes it, and connect the result "
                    "to the decision the learner must make."
                ),
            ),
            CanvasBlock(
                id="metrics-study-support-2",
                type="list",
                items=[
                    "Name the source variable or formula before interpreting it.",
                    "Explain which part comes from evidence and which part is a modeling choice.",
                    "Check how the conclusion would change under a different cost or observation.",
                ],
            ),
            CanvasBlock(
                id="metrics-study-support-3",
                type="callout",
                text=(
                    f"Learning checkpoint: use {anchor} to rephrase the section without slide wording. "
                    "A good answer should include the mechanism, a concrete example, and one limitation "
                    "or failure mode."
                ),
            ),
        ]
    )

    normalized = normalize_learning_support(document)

    paragraph, list_block, callout = normalized.sections[0].blocks
    assert paragraph.text == support_why_text("Measuring Binary Classifier Performance", anchor)
    assert list_block.items == support_study_items()
    assert callout.text == support_check_prompt("Measuring Binary Classifier Performance")
    all_text = "\n".join([paragraph.text or "", callout.text or "", *list_block.items])
    assert "Learning checkpoint: use" not in all_text
    assert "turns the source material into a decision step" not in all_text
    assert "rephrase the section" not in all_text


def test_course_canvas_store_writes_clean_learning_support(tmp_path: Path) -> None:
    store = CourseCanvasStore(StorageLayout(tmp_path / "workspaces"))
    document = _document(
        [
            CanvasBlock(
                id="metrics-study-support-3",
                type="callout",
                text=(
                    "Learning checkpoint: use In binary classification, we categorize outcomes into four cases: "
                    "True Positives (TP), to rephrase the section without slide wording. A good answer should "
                    "include the mechanism, a concrete example, and one limitation or failure mode."
                ),
            )
        ]
    )

    written = store.write(document)
    section_path = next(store.path("martius-ml", "lecture-02").joinpath("sections").glob("*.md"))

    assert written.sections[0].blocks[0].text == support_check_prompt("Measuring Binary Classifier Performance")
    assert "Learning checkpoint: use" not in section_path.read_text(encoding="utf-8")


def _document(blocks: list[CanvasBlock]) -> CanvasDocument:
    return CanvasDocument(
        id="martius-ml-lecture-02",
        course_id="martius-ml",
        lecture_id="lecture-02",
        title="Generalization and Model Selection",
        source_kind="generated",
        source_ref="test",
        workspace_path="canvas/index.md",
        sections=[
            CanvasSection(
                id="measuring-binary-classifier-performance",
                title="Measuring Binary Classifier Performance",
                source_ref="frames 18-21",
                blocks=blocks,
            )
        ],
    )

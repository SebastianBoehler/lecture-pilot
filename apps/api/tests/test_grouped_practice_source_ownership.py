from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from test_practice_design_canvas_hardening import _design, _source_section


def test_grouped_sources_preserve_anchor_ownership(tmp_path):
    from lecturepilot.authoring_workspace import AuthoringWorkspace

    design = _design()
    sections = [
        _source_section("transcript", "Unrelated transcript.").model_copy(
            update={"source_ref": "audio.txt"}
        ),
        _source_section("evidence", "The cited evidence supports the conclusion."),
        *[_source_section(f"other-{i}", f"Other material {i}.") for i in range(8)],
    ]
    source = CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="markdown",
        source_ref="bundle",
        workspace_path="source/index.md",
        sections=sections,
    )
    workspace = AuthoringWorkspace(tmp_path, source, design, lambda: None)
    assert workspace.targets["evidence-batch-1"] == design.targets


def test_checkpoint_accepts_approved_source_after_another_source_in_group():
    from lecturepilot.course_practice_design_validation import validate_canvas_practice_contract

    design = _design()
    document = CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="generated",
        source_ref="bundle",
        workspace_path="source/index.md",
        sections=[
            CanvasSection(
                id="learning",
                title="Learning",
                source_ref="audio.txt | lecture-01.md",
                blocks=[
                    CanvasBlock(
                        id=f"practice-{design.targets[0].id}",
                        type="checkpoint",
                        text=design.targets[0].baseline_task,
                    )
                ],
            )
        ],
    )
    validate_canvas_practice_contract(document, design)

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.learning_map import build_learning_map


def test_learning_map_derives_ordered_concepts_checkpoints_and_quizzes() -> None:
    document = CanvasDocument(
        id="course-lecture-03",
        course_id="course",
        lecture_id="lecture-03",
        title="Lecture 03",
        source_kind="generated",
        source_ref="source.md",
        workspace_path="/tmp/index.md",
        sections=[
            CanvasSection(
                id="bayesian-decision-theory-the-aim",
                title="Intro",
                source_ref="source.md#intro",
                blocks=[
                    CanvasBlock(
                        id="intro-check",
                        type="checkpoint",
                        caption="Intro gate",
                        text="Explain the learning setup.",
                    )
                ],
            ),
            CanvasSection(
                id="losses-and-risks",
                title="Risk",
                source_ref="source.md#risk",
                blocks=[
                    CanvasBlock(
                        id="risk-quiz",
                        type="quiz",
                        text="Which action minimizes risk?",
                        items=["A", "B"],
                        answer_index=1,
                    )
                ],
            ),
        ],
    )

    learning_map = build_learning_map(document)

    assert [node.id for node in learning_map.nodes] == [
        "bayesian-decision-theory-the-aim",
        "losses-and-risks",
    ]
    assert learning_map.nodes[0].gate_ids == ["intro-check"]
    assert learning_map.nodes[1].prerequisites == ["bayesian-decision-theory-the-aim"]
    assert learning_map.nodes[1].quiz_ids == ["risk-quiz"]
    assert learning_map.gates[0].prompt == "Explain the learning setup."
    assert [gate.id for gate in learning_map.gates] == ["intro-check"]


def test_learning_map_bounds_generated_checkpoint_titles() -> None:
    long_caption = "Confirm the learner can explain the mechanism. " * 6
    document = CanvasDocument(
        id="course-lecture-01",
        course_id="course",
        lecture_id="lecture-01",
        title="Lecture 01",
        source_kind="generated",
        source_ref="source.md",
        workspace_path="/tmp/index.md",
        sections=[
            CanvasSection(
                id="introduction",
                title="Introduction",
                blocks=[
                    CanvasBlock(
                        id="intro-check",
                        type="checkpoint",
                        caption=long_caption,
                        text="Explain the evidence in your own words. " * 40,
                    )
                ],
            )
        ],
    )

    learning_map = build_learning_map(document)

    assert learning_map.gates[0].title == long_caption[:200]
    assert len(learning_map.gates[0].prompt) == 1000


def test_learning_map_only_counts_assessments_as_quizzes() -> None:
    document = CanvasDocument(
        id="course-lecture-02",
        course_id="course",
        lecture_id="lecture-02",
        title="Lecture 02",
        source_kind="generated",
        source_ref="source.md",
        workspace_path="/tmp/index.md",
        sections=[
            CanvasSection(
                id="decision-boundaries",
                title="Decision boundaries",
                blocks=[
                    CanvasBlock(
                        id="risk-chart",
                        type="component",
                        component_id="risk-chart",
                        component_type="interactive_chart",
                        component_ref="components/risk-chart.yaml",
                        component_version=1,
                    ),
                    CanvasBlock(
                        id="risk-process",
                        type="component",
                        component_id="risk-process",
                        component_type="process_explorer",
                        component_ref="components/risk-process.yaml",
                        component_version=1,
                    ),
                    CanvasBlock(
                        id="risk-choice",
                        type="component",
                        component_id="risk-choice",
                        component_type="single_choice_quiz",
                        component_ref="components/risk-choice.yaml",
                        component_version=1,
                    ),
                ],
            )
        ],
    )

    learning_map = build_learning_map(document)

    assert learning_map.nodes[0].quiz_ids == ["risk-choice"]


def test_learning_map_uses_checkpoint_contract_for_later_lectures() -> None:
    document = CanvasDocument(
        id="course-lecture-14",
        course_id="course",
        lecture_id="lecture-14",
        title="Lecture 14",
        source_kind="generated",
        source_ref="source.md",
        workspace_path="/tmp/index.md",
        sections=[
            CanvasSection(
                id="causal-transfer",
                title="Causal transfer",
                blocks=[
                    CanvasBlock(
                        id="causal-transfer-check",
                        type="checkpoint",
                        caption="Transfer check",
                        text="Explain when the causal conclusion transfers to a new setting.",
                    )
                ],
            )
        ],
    )

    first = build_learning_map(document)
    second = build_learning_map(document)

    assert first.nodes[0].gate_ids == ["causal-transfer-check"]
    assert first.gates[0].id == "causal-transfer-check"
    assert first.gates[0].evidence_criteria[0].description == (
        "Explain when the causal conclusion transfers to a new setting."
    )
    assert first.gates[0].review_after_days == 2
    assert first.gates[0].revision == second.gates[0].revision
    assert first.revision == second.revision

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
    assert learning_map.nodes[0].gate_ids == ["intro-check", "bayes-decision-check"]
    assert learning_map.nodes[1].prerequisites == ["bayesian-decision-theory-the-aim"]
    assert learning_map.nodes[1].quiz_ids == ["risk-quiz"]
    assert learning_map.gates[0].prompt == "Explain the learning setup."
    assert [gate.id for gate in learning_map.gates].count("bayes-decision-check") == 1

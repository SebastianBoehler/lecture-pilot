"""Self-contained assessment fixtures using the current explicit checkpoint contract."""

from dataclasses import dataclass

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.learning_map_models import (
    LearningMap,
    LearningMapGate,
    LearningMapNode,
)
from lecturepilot.models import (
    AgentAnalyticsContext,
    AgentCoachingContext,
    AgentTurnInput,
    AttendanceStatus,
    CanvasState,
)


@dataclass(frozen=True)
class GateScenario:
    lecture_id: str
    label: str
    attendance: AttendanceStatus
    message: str
    expected_status: str


SCENARIOS = (
    GateScenario(
        "lecture-01",
        "weak_intro_answer",
        AttendanceStatus.PRESENT,
        "Machine learning predicts labels from examples.",
        "needs_evidence",
    ),
    GateScenario(
        "lecture-01",
        "strong_intro_answer",
        AttendanceStatus.PRESENT,
        (
            "Supervised classification predicts a target label from training data. "
            "A model is optimized with a loss, then validation or test data checks generalization."
        ),
        "passed",
    ),
    GateScenario(
        "lecture-02",
        "weak_generalization_answer",
        AttendanceStatus.ABSENT,
        "Generalization means the model works later.",
        "needs_evidence",
    ),
    GateScenario(
        "lecture-02",
        "strong_generalization_answer",
        AttendanceStatus.PRESENT,
        (
            "We train on training data, use validation or held-out test data to estimate "
            "generalization, and inspect false positive or recall rates because the classifier "
            "threshold changes the decision rates."
        ),
        "passed",
    ),
    GateScenario(
        "lecture-03",
        "weak_bayes_answer",
        AttendanceStatus.PRESENT,
        "The posterior is P(C|X), so Bayes updates a belief.",
        "needs_evidence",
    ),
    GateScenario(
        "lecture-03",
        "strong_bayes_answer",
        AttendanceStatus.PRESENT,
        (
            "The posterior P(C|X) combines prior, likelihood, and evidence P(X). "
            "The classifier then chooses a decision, while loss or false-positive cost "
            "changes the risk-sensitive threshold."
        ),
        "passed",
    ),
)


# Author-written fixtures, not a released course or an efficacy evaluation.
SCENARIOS += (
    GateScenario(
        "lecture-01",
        "paraphrase_intro",
        AttendanceStatus.PRESENT,
        "Predict a category for each input. Fit parameters on labeled examples to reduce prediction error, then evaluate on unseen examples to check whether the rule works beyond the fitting set.",
        "passed",
    ),
    GateScenario(
        "lecture-02",
        "keywords_wrong_direction",
        AttendanceStatus.PRESENT,
        "Training fits the model; held-out validation estimates generalization. Lowering the threshold always lowers false-positive rate because recall improves.",
        "needs_evidence",
    ),
    GateScenario(
        "lecture-03",
        "bayes_wrong_cost",
        AttendanceStatus.PRESENT,
        "The posterior equals likelihood times prior divided by evidence. Increasing false-positive loss means we should lower the positive threshold to predict more positives.",
        "needs_evidence",
    ),
    GateScenario(
        "lecture-01",
        "uncertain_incomplete",
        AttendanceStatus.PRESENT,
        "I am unsure: labels are targets, but I cannot explain loss or how to evaluate on unseen data.",
        "needs_evidence",
    ),
)


def _turn_for_scenario(scenario: GateScenario) -> AgentTurnInput:
    gate = _gate_for_lecture(scenario.lecture_id)
    canvas = _canvas_for_lecture(scenario.lecture_id)
    learning_map = LearningMap.create(
        course_id=canvas.course_id,
        lecture_id=canvas.lecture_id,
        title=canvas.title,
        objective=gate.prompt,
        gates=[gate],
        nodes=[
            LearningMapNode(
                id=gate.section_id,
                title=gate.title,
                lecture_id=canvas.lecture_id,
                section_id=gate.section_id,
                source_ref=gate.source_ref,
                prerequisites=[],
                gate_ids=[gate.id],
                quiz_ids=[],
            )
        ],
    )
    return AgentTurnInput(
        user_id="provider-benchmark-user",
        course_id="martius-ml",
        lecture_id=scenario.lecture_id,
        attendance=scenario.attendance,
        message=scenario.message,
        canvas_state=CanvasState(
            focused_section_id=_focused_section_id(scenario.lecture_id)
        ),
        canvas_context=_canvas_for_lecture(scenario.lecture_id),
        active_gate=gate,
        checkpoint_gate_id=gate.id,
        analytics_context=AgentAnalyticsContext(
            publication_version=1, learning_map_revision=learning_map.revision
        ),
        coaching_context=AgentCoachingContext(
            active_gate_id=gate.id,
            active_gate_revision=gate.revision,
            pending_check_gate_id=gate.id,
            pending_check_gate_revision=gate.revision,
            pending_check_issued_at="2026-08-18T08:00:00+00:00",
            pending_check_prompt=gate.prompt,
            pending_check_task_id="independent-exit",
            pending_check_stage="independent_exit",
        ),
    )


def _gate_for_lecture(lecture_id: str) -> LearningMapGate:
    section_id = _focused_section_id(lecture_id)
    if lecture_id == "lecture-01":
        criteria = [
            {"id": "target", "description": "Identifies prediction of a target label."},
            {"id": "loss", "description": "Explains model optimization using a loss."},
            {
                "id": "generalization",
                "description": "Uses held-out validation or test data to check generalization.",
            },
        ]
    elif lecture_id == "lecture-02":
        criteria = [
            {
                "id": "held-out",
                "description": "Distinguishes training from held-out generalization evaluation.",
            },
            {
                "id": "threshold-errors",
                "description": "Connects classifier threshold choice to an error rate.",
            },
        ]
    else:
        criteria = [
            {
                "id": "bayes-components",
                "description": "Connects prior, likelihood, evidence, and posterior.",
            },
            {
                "id": "risk-decision",
                "description": "Connects loss or error cost to the decision threshold.",
            },
        ]
    return LearningMapGate.create(
        id=f"{section_id}-gate",
        concept_id=section_id,
        title=f"{section_id} evidence check",
        prompt=" ".join(item["description"] for item in criteria),
        evidence_criteria=criteria,
        transfer_prompt="Apply the explanation to a changed example.",
        review_after_days=3,
        section_id=section_id,
        source_ref="benchmark scenario",
    )


def _canvas_for_lecture(lecture_id: str) -> CanvasDocument:
    section_id, title, text = _canvas_seed(lecture_id)
    return CanvasDocument(
        id=f"benchmark-{lecture_id}",
        course_id="martius-ml",
        lecture_id=lecture_id,
        title=title,
        source_kind="generated",
        source_ref="benchmark scenario",
        workspace_path=f".lecturepilot/benchmark/{lecture_id}/canvas/index.md",
        sections=[
            CanvasSection(
                id=section_id,
                title=title,
                blocks=[
                    CanvasBlock(id=f"{section_id}-p-1", type="paragraph", text=text)
                ],
            )
        ],
    )


def _canvas_seed(lecture_id: str) -> tuple[str, str, str]:
    if lecture_id == "lecture-01":
        return (
            "what-is-machine-learning",
            "Machine learning setup",
            "Supervised classification predicts labels from examples. Model parameters are fitted by optimizing a loss on training data. Held-out validation or test data assess generalization to unseen examples.",
        )
    if lecture_id == "lecture-02":
        return (
            "generalization-foundations",
            "Generalization and classifier evaluation",
            "Training data fit the model. Held-out data estimate performance on unseen cases. Lowering a positive-class score threshold predicts more positives, increasing or preserving both recall and the false-positive rate on a fixed evaluation set.",
        )
    return (
        "bayesian-decision-theory-the-aim",
        "Bayesian decision theory",
        "Bayes gives P(C|X) = P(X|C) P(C) / P(X): posterior from likelihood, prior and evidence. A decision minimizes expected loss under this posterior. Raising the false-positive cost favors a higher positive-class posterior threshold.",
    )


def _focused_section_id(lecture_id: str) -> str:
    return _canvas_seed(lecture_id)[0]

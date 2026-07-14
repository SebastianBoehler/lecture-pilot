from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceRule:
    label: str
    required_terms: tuple[tuple[str, ...], ...]

    def matches(self, text: str) -> bool:
        return all(
            any(term in text for term in alternatives) for alternatives in self.required_terms
        )


@dataclass(frozen=True)
class GateTarget:
    section_id: str
    span_id: str
    highlight_text: str


@dataclass(frozen=True)
class GateSpec:
    lecture_id: str
    gate_id: str
    title: str
    rules: tuple[EvidenceRule, ...]
    pending_target: GateTarget
    passed_target: GateTarget


@dataclass(frozen=True)
class GateEvaluation:
    spec: GateSpec
    missing_labels: tuple[str, ...]

    @property
    def is_complete(self) -> bool:
        return not self.missing_labels

    @property
    def next_missing_label(self) -> str:
        return self.missing_labels[0] if self.missing_labels else "next applied example"


def evaluate_learning_gate(lecture_id: str, message: str) -> GateEvaluation:
    spec = gate_spec_for_lecture(lecture_id)
    normalized = message.lower()
    missing = tuple(rule.label for rule in spec.rules if not rule.matches(normalized))
    return GateEvaluation(spec=spec, missing_labels=missing)


def gate_spec_for_lecture(lecture_id: str) -> GateSpec:
    return _GATE_SPECS.get(lecture_id, _DEFAULT_SPEC)


def gate_rubric_context(lecture_id: str) -> str:
    spec = gate_spec_for_lecture(lecture_id)
    labels = "\n".join(f"- {rule.label}" for rule in spec.rules)
    return (
        f"Active quality gate: {spec.gate_id} ({spec.title})\n"
        "Required evidence groups for a pass:\n"
        f"{labels}\n"
        "Mark passed only when the student's answer covers all groups. "
        "When all groups are covered, return passed without asking for bonus examples. "
        "Do not add extra pass requirements beyond these groups. "
        "If exactly one or two groups are missing, return needs_evidence and ask for the first "
        "missing group only."
    )


_LECTURE_01_SPEC = GateSpec(
    lecture_id="lecture-01",
    gate_id="lecture-learning-outcome-check",
    title="Machine learning setup",
    rules=(
        EvidenceRule(
            "learning task and prediction target",
            (
                ("supervised", "classification", "regression", "unsupervised", "reinforcement"),
                ("target", "label", "output", "prediction", "predict"),
            ),
        ),
        EvidenceRule(
            "data, model, and loss connection",
            (
                ("data", "dataset", "examples", "training"),
                ("model", "hypothesis", "algorithm"),
                ("loss", "error", "objective", "optimize"),
            ),
        ),
        EvidenceRule(
            "generalization or held-out evaluation",
            (("generalization", "validation", "test", "held-out", "overfit"),),
        ),
    ),
    pending_target=GateTarget(
        "what-is-machine-learning",
        "what-is-machine-learning-p-1",
        "machine learning",
    ),
    passed_target=GateTarget(
        "components-of-supervised-machine-learning",
        "components-of-supervised-machine-learning-p-1",
        "loss",
    ),
)

_LECTURE_02_SPEC = GateSpec(
    lecture_id="lecture-02",
    gate_id="lecture-learning-outcome-check",
    title="Generalization and classifier evaluation",
    rules=(
        EvidenceRule(
            "train, validation, and test split",
            (
                ("train", "training"),
                ("validation", "test", "held-out"),
            ),
        ),
        EvidenceRule(
            "generalization or overfitting risk",
            (("generalization", "overfit", "variance", "no free lunch"),),
        ),
        EvidenceRule(
            "classification metric or threshold consequence",
            (
                ("false positive", "false negative", "precision", "recall", "accuracy"),
                ("threshold", "decision", "classifier", "rate"),
            ),
        ),
    ),
    pending_target=GateTarget(
        "generalization-foundations",
        "generalization-foundations-p-1",
        "generalization",
    ),
    passed_target=GateTarget(
        "binary-classifier-metrics",
        "binary-classifier-metrics-p-1",
        "false positive",
    ),
)

_LECTURE_03_SPEC = GateSpec(
    lecture_id="lecture-03",
    gate_id="bayes-decision-check",
    title="Bayesian decision theory",
    rules=(
        EvidenceRule(
            "posterior from evidence",
            (("posterior", "p(c|x", "p(c | x"),),
        ),
        EvidenceRule(
            "prior, likelihood, and evidence",
            (
                ("prior",),
                ("likelihood",),
                ("evidence", "p(x)", "normalizer"),
            ),
        ),
        EvidenceRule(
            "classifier decision",
            (("decision", "classif", "predict", "choose"),),
        ),
        EvidenceRule(
            "risk or cost",
            (("risk", "cost", "loss", "false positive", "false negative"),),
        ),
    ),
    pending_target=GateTarget(
        "bayesian-decision-theory-the-aim",
        "bayesian-decision-theory-the-aim-p-1",
        "decisions",
    ),
    passed_target=GateTarget("losses-and-risks", "losses-and-risks-list", "decision"),
)

_DEFAULT_SPEC = GateSpec(
    lecture_id="default",
    gate_id="lecture-learning-outcome-check",
    title="Lecture learning outcome",
    rules=(
        EvidenceRule("key concept definition", (("define", "concept", "means"),)),
        EvidenceRule("mechanism or worked step", (("because", "therefore", "step"),)),
        EvidenceRule("application or failure mode", (("example", "apply", "fails", "risk"),)),
    ),
    pending_target=GateTarget("learning-goals", "learning-goals-p-1", "learning goal"),
    passed_target=GateTarget("learning-goals", "learning-goals-p-1", "application"),
)

_GATE_SPECS = {
    spec.lecture_id: spec
    for spec in (
        _LECTURE_01_SPEC,
        _LECTURE_02_SPEC,
        _LECTURE_03_SPEC,
    )
}

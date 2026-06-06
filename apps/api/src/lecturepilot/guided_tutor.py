from __future__ import annotations

from dataclasses import dataclass

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    AttendanceStatus,
    CanvasCommand,
    QualityGateDecision,
    QualityGateStatus,
)


LOCAL_PREVIEW_USER_ID = "local-preview-user"
_BAYES_GATE_ID = "bayes-decision-check"


@dataclass(frozen=True)
class TopicTarget:
    section_id: str
    span_id: str
    highlight_text: str


def run_local_preview_turn(turn: AgentTurnInput) -> AgentTurnResult:
    learning_mode = _learning_mode(turn)
    if _asks_for_soccer_example(turn.message):
        section = _soccer_bayes_section()
        return AgentTurnResult(
            message=(
                f"{learning_mode} I added a soccer scouting example to your personal canvas "
                "and focused it. Use it to explain posterior, risk, and the final decision."
            ),
            canvas_commands=[
                CanvasCommand(type="append_section", section_id=section.id, section=section),
                CanvasCommand(type="focus_section", section_id=section.id),
                CanvasCommand(
                    type="highlight_span",
                    section_id=section.id,
                    span_id=f"{section.id}-p-1",
                    highlight_text="evidence X",
                ),
            ],
            quality_gate=QualityGateDecision(
                gate_id=_BAYES_GATE_ID,
                status=QualityGateStatus.NEEDS_EVIDENCE,
                reason="The learner asked for a personalized transfer example.",
                next_prompt="Use the soccer example to identify prior, likelihood, posterior, and cost.",
            ),
            model="local-guided-preview",
        )

    evidence = _read_bayes_gate_evidence(turn.message)
    if evidence.is_complete:
        return AgentTurnResult(
            message=(
                "Gate passed: you connected Bayes terms to the decision and risk. I focused "
                "the risk-decision part so the next step is to apply it to one example."
            ),
            canvas_commands=[
                CanvasCommand(type="focus_section", section_id="losses-and-risks"),
                CanvasCommand(
                    type="highlight_span",
                    section_id="losses-and-risks",
                    span_id="losses-and-risks-list",
                    highlight_text="decision",
                ),
            ],
            quality_gate=QualityGateDecision(
                gate_id=_BAYES_GATE_ID,
                status=QualityGateStatus.PASSED,
                reason="The learner explained posterior, prior, likelihood, evidence, and decision risk.",
                next_prompt="Apply the decision rule to a concrete classification case.",
            ),
            model="local-guided-preview",
        )

    missing = ", ".join(evidence.missing_labels)
    target = _topic_target(turn.message)
    return AgentTurnResult(
        message=(
            f"{learning_mode} Gate pending: explain how Bayes' formula turns evidence into a posterior, "
            f"then say how costs or risk change the final classifier decision. Missing evidence: {missing}."
        ),
        canvas_commands=[
            CanvasCommand(type="focus_section", section_id=target.section_id),
            CanvasCommand(
                type="highlight_span",
                section_id=target.section_id,
                span_id=target.span_id,
                highlight_text=target.highlight_text,
            ),
        ],
        quality_gate=QualityGateDecision(
            gate_id=_BAYES_GATE_ID,
            status=QualityGateStatus.NEEDS_EVIDENCE,
            reason=f"Missing evidence: {missing}.",
            next_prompt=(
                "Answer with posterior, prior, likelihood, evidence, and one risk-sensitive decision."
            ),
        ),
        model="local-guided-preview",
    )


def _mentions_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _topic_target(message: str) -> TopicTarget:
    normalized = message.lower()
    if _mentions_any(
        normalized,
        ("risk", "cost", "loss", "false positive", "false negative", "threshold", "reject"),
    ):
        return TopicTarget("losses-and-risks", "losses-and-risks-list", "costly")
    if _mentions_any(normalized, ("spam", "naive", "filter", "independence")):
        return TopicTarget("naive-bayes-classifiers", "naive-bayes-classifiers-p-1", "Naive Bayes")
    if _mentions_any(normalized, ("decision", "classif", "predict", "choose")):
        return TopicTarget("losses-and-risks", "losses-and-risks-list", "decision")
    if _mentions_any(normalized, ("posterior", "prior", "likelihood", "evidence", "formula", "p(c|x")):
        return TopicTarget("bayes-formula", "bayes-formula-list", "probability")
    return TopicTarget(
        "bayesian-decision-theory-the-aim",
        "bayesian-decision-theory-the-aim-p-1",
        "decisions",
    )


@dataclass(frozen=True)
class BayesGateEvidence:
    has_posterior: bool
    has_bayes_terms: bool
    has_decision: bool
    has_risk_or_cost: bool

    @property
    def is_complete(self) -> bool:
        return all((self.has_posterior, self.has_bayes_terms, self.has_decision, self.has_risk_or_cost))

    @property
    def missing_labels(self) -> tuple[str, ...]:
        missing = []
        if not self.has_posterior:
            missing.append("posterior from evidence")
        if not self.has_bayes_terms:
            missing.append("prior, likelihood, and evidence")
        if not self.has_decision:
            missing.append("classifier decision")
        if not self.has_risk_or_cost:
            missing.append("risk or cost")
        return tuple(missing)


def _read_bayes_gate_evidence(message: str) -> BayesGateEvidence:
    normalized = message.lower()
    return BayesGateEvidence(
        has_posterior="posterior" in normalized or "p(c|x" in normalized or "p(c | x" in normalized,
        has_bayes_terms=_mentions_any(normalized, ("prior", "likelihood")) and _mentions_any(
            normalized, ("evidence", "p(x)", "normalizer")
        ),
        has_decision=_mentions_any(normalized, ("decision", "classif", "predict", "choose")),
        has_risk_or_cost=_mentions_any(normalized, ("risk", "cost", "loss", "false positive")),
    )


def _asks_for_soccer_example(message: str) -> bool:
    normalized = message.lower()
    return _mentions_any(normalized, ("soccer", "football", "spieler", "verein"))


def _learning_mode(turn: AgentTurnInput) -> str:
    if turn.attendance == AttendanceStatus.PRESENT:
        return "Verification mode: you marked yourself present, so I will check understanding before reteaching."
    if turn.attendance == AttendanceStatus.ABSENT:
        return "Guided walkthrough mode: you marked yourself absent, so I will teach from the lecture material."
    return "Diagnostic mode: attendance is unknown, so I will first locate the missing concept."


def _soccer_bayes_section() -> CanvasSection:
    return CanvasSection(
        id="student-soccer-bayes-example",
        title="Soccer scouting example",
        source_ref="student workspace",
        blocks=[
            CanvasBlock(
                id="student-soccer-bayes-example-p-1",
                type="paragraph",
                text=(
                    "Treat a scouting report as evidence X and the hidden event C as whether "
                    "a player will fit the team. Bayes updates the prior belief into a posterior "
                    "after observing the report, match data, and training signals."
                ),
            ),
            CanvasBlock(
                id="student-soccer-bayes-example-list",
                type="list",
                items=[
                    "Prior: the base chance that a player succeeds before the new report.",
                    "Likelihood: how probable this report is if the player truly fits.",
                    "Evidence: how common this report is across all players.",
                    "Decision risk: missing a strong player and signing a poor fit have different costs.",
                ],
            ),
        ],
    )

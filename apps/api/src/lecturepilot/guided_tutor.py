from __future__ import annotations

from dataclasses import dataclass

from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    CanvasCommand,
    QualityGateDecision,
    QualityGateStatus,
)


LOCAL_PREVIEW_USER_ID = "local-preview-user"
_KERNEL_GATE_ID = "kernel-skill-check"


@dataclass(frozen=True)
class KernelGateEvidence:
    has_replacement: bool
    has_feature_space: bool
    has_computation_reason: bool
    has_transfer_or_failure: bool

    @property
    def is_complete(self) -> bool:
        return all(
            (
                self.has_replacement,
                self.has_feature_space,
                self.has_computation_reason,
                self.has_transfer_or_failure,
            )
        )

    @property
    def missing_labels(self) -> tuple[str, ...]:
        missing = []
        if not self.has_replacement:
            missing.append("what k(x, x') replaces")
        if not self.has_feature_space:
            missing.append("feature-space mechanism")
        if not self.has_computation_reason:
            missing.append("computational reason")
        if not self.has_transfer_or_failure:
            missing.append("concrete example or failure mode")
        return tuple(missing)


def run_local_preview_turn(turn: AgentTurnInput) -> AgentTurnResult:
    evidence = _read_kernel_gate_evidence(turn.message)
    if evidence.is_complete:
        return AgentTurnResult(
            message=(
                "Gate passed: you gave the definition, feature-space mechanism, computation "
                "reason, and transfer check. I moved the canvas to the kernel trick; next gate "
                "is a worked failure-mode example."
            ),
            canvas_commands=[CanvasCommand(type="focus_section", section_id="kernel-trick")],
            quality_gate=QualityGateDecision(
                gate_id=_KERNEL_GATE_ID,
                status=QualityGateStatus.PASSED,
                reason=(
                    "The student explained replacement, feature space, computation, "
                    "and transfer or failure mode."
                ),
                next_prompt="Apply the same idea to one kernel failure mode.",
            ),
            model="local-guided-preview",
        )

    missing = ", ".join(evidence.missing_labels)
    return AgentTurnResult(
        message=(
            "Gate pending: answer this check with all parts before we move on. State what "
            "k(x, x') replaces, explain why implicit phi(x) saves computation, and give one "
            f"concrete example or failure mode. Missing evidence: {missing}."
        ),
        canvas_commands=[CanvasCommand(type="focus_section", section_id="skill-check")],
        quality_gate=QualityGateDecision(
            gate_id=_KERNEL_GATE_ID,
            status=QualityGateStatus.NEEDS_EVIDENCE,
            reason=f"Missing evidence: {missing}.",
            next_prompt=(
                "Answer with replacement, feature-space mechanism, computation reason, "
                "and one example or failure mode."
            ),
        ),
        model="local-guided-preview",
    )


def _read_kernel_gate_evidence(message: str) -> KernelGateEvidence:
    normalized = message.lower()
    has_kernel_symbol = "k(x" in normalized or "kernel" in normalized
    has_inner_product = "inner product" in normalized or "dot product" in normalized
    has_feature_space = _mentions_any(
        normalized,
        ("feature space", "phi", "lift", "mapped representation", "lifted representation"),
    )
    has_computation_reason = _mentions_any(
        normalized,
        ("avoid", "without", "implicit", "not build", "do not build", "don't build", "skip"),
    ) and _mentions_any(
        normalized,
        ("comput", "expensive", "high-dimensional", "coordinates", "explicit expansion"),
    )
    has_transfer_or_failure = _mentions_any(
        normalized,
        (
            "for ",
            "example",
            "classification",
            "if ",
            "only works",
            "wrong tool",
            "failure",
            "invalid",
            "does not match",
            "matches the task",
            "similarity matches",
        ),
    )
    return KernelGateEvidence(
        has_replacement=has_kernel_symbol and has_inner_product,
        has_feature_space=has_feature_space,
        has_computation_reason=has_computation_reason,
        has_transfer_or_failure=has_transfer_or_failure,
    )


def _mentions_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)

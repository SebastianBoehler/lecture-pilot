from __future__ import annotations

from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    CanvasCommand,
    QualityGateDecision,
    QualityGateStatus,
)


LOCAL_PREVIEW_USER_ID = "local-preview-user"
_KERNEL_GATE_ID = "kernel-skill-check"


def run_local_preview_turn(turn: AgentTurnInput) -> AgentTurnResult:
    if _has_kernel_gate_evidence(turn.message):
        return AgentTurnResult(
            message=(
                "Gate passed: you identified that k(x, x') stands in for the inner product "
                "phi(x) dot phi(x') in feature space. Next checkpoint: explain why avoiding "
                "explicit phi(x) is computationally useful in one sentence."
            ),
            canvas_commands=[CanvasCommand(type="focus_section", section_id="kernel-trick")],
            quality_gate=QualityGateDecision(
                gate_id=_KERNEL_GATE_ID,
                status=QualityGateStatus.PASSED,
                reason="The student connected k(x, x') to the feature-space inner product.",
                next_prompt="Explain the computation saved by avoiding explicit phi(x).",
            ),
            model="local-guided-preview",
        )

    return AgentTurnResult(
        message=(
            "Start here: a kernel is a shortcut for comparing examples after an implicit "
            "feature-map lift. Gate pending: answer this check in one sentence: in the kernel "
            "trick, what does k(x, x') replace? Use the words inner product or feature space."
        ),
        canvas_commands=[CanvasCommand(type="focus_section", section_id="skill-check")],
        quality_gate=QualityGateDecision(
            gate_id=_KERNEL_GATE_ID,
            status=QualityGateStatus.NEEDS_EVIDENCE,
            reason="The student has not yet stated what k(x, x') replaces.",
            next_prompt="State what k(x, x') replaces in one sentence.",
        ),
        model="local-guided-preview",
    )


def _has_kernel_gate_evidence(message: str) -> bool:
    normalized = message.lower()
    has_kernel_symbol = "k(x" in normalized or "kernel" in normalized
    has_inner_product = "inner product" in normalized or "dot product" in normalized
    has_feature_space = "feature space" in normalized or "phi" in normalized
    return has_kernel_symbol and has_inner_product and has_feature_space

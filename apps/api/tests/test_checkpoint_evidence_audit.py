import json
from datetime import UTC, datetime

import pytest

from lecturepilot.checkpoint_evidence_audit import (
    CriterionQuote,
    validate_evidence_quotes,
    append_assessment_audit,
)
from lecturepilot.models import QualityGateDecision, QualityGateStatus
from lecturepilot.providers import ProviderConfigurationError
from types import SimpleNamespace


def test_quote_validation_requires_verbatim_answer_and_claimed_criterion():
    quote = CriterionQuote(evidence_id="cause", quote="the cause produces the effect")
    validate_evidence_quotes([quote], evidence_ids=["cause"], answer=quote.quote, required=True)
    for quotes, answer in [([], quote.quote), ([quote], "unrelated answer")]:
        with pytest.raises(ProviderConfigurationError):
            validate_evidence_quotes(quotes, evidence_ids=["cause"], answer=answer, required=True)


@pytest.mark.parametrize(
    "quote,answer",
    [
        ("a", "a is part of a long unrelated answer"),
        ("risk increases", "Selected option: risk increases\nReasoning: I do not know."),
    ],
)
def test_quote_audit_rejects_trivial_or_option_only_anchors(quote, answer):
    with pytest.raises(ProviderConfigurationError):
        validate_evidence_quotes(
            [CriterionQuote(evidence_id="cause", quote=quote)],
            evidence_ids=["cause"],
            answer=answer,
            required=True,
        )


def test_private_quotations_are_excluded_from_decision_serialization(tmp_path):
    quote = CriterionQuote(evidence_id="cause", quote="the cause produces the effect")
    decision = QualityGateDecision(
        gate_id="gate",
        gate_revision="a" * 64,
        status=QualityGateStatus.PASSED,
        reason="Approved criteria passed.",
        evidence_ids=["cause"],
        missing_evidence_ids=[],
        evidence_quotes=[quote],
    )
    assert "evidence_quotes" not in decision.model_dump()
    now = datetime.now(UTC)
    path = tmp_path / "assessment-audit.jsonl"
    append_assessment_audit(
        path,
        pending=SimpleNamespace(issued_at=now),
        event=SimpleNamespace(
            created_at=now,
            gate_id="gate",
            gate_revision="a" * 64,
            task_id="independent-exit",
            attempt_index=1,
            attempt_kind="independent_exit",
        ),
        quotes=decision.evidence_quotes,
        publication_version=2,
    )
    payload = json.loads(path.read_text())
    assert payload["publication_version"] == 2
    assert payload["evidence_quotes"][0]["quote"] == quote.quote

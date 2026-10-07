"""Private, verbatim answer anchors; raw excerpts never enter categorical analytics."""

import json

from lecturepilot.checkpoint_evidence_models import CriterionQuote as CriterionQuote

from lecturepilot.durable_files import atomic_write_text
from lecturepilot.providers import ProviderConfigurationError


def validate_evidence_quotes(quotes, *, evidence_ids, answer, required):
    ids = [item.evidence_id for item in quotes]
    if len(ids) != len(set(ids)) or set(ids) - set(evidence_ids):
        raise ProviderConfigurationError(
            "Assessment quotations must match distinct claimed evidence IDs."
        )
    if required and set(ids) != set(evidence_ids):
        raise ProviderConfigurationError(
            "Each demonstrated checkpoint criterion requires an answer quotation."
        )
    if any(not item.quote.strip() or item.quote not in answer for item in quotes):
        raise ProviderConfigurationError(
            "Assessment quotations must appear verbatim in the current answer."
        )


def append_assessment_audit(path, *, pending, event, quotes, publication_version):
    if not quotes:
        return
    payload = {
        "created_at": event.created_at.isoformat(),
        "gate_id": event.gate_id,
        "gate_revision": event.gate_revision,
        "task_id": event.task_id,
        "publication_version": publication_version,
        "issued_at": pending.issued_at.isoformat(),
        "attempt_index": event.attempt_index,
        "attempt_kind": event.attempt_kind,
        "evidence_quotes": [item.model_dump() for item in quotes],
    }
    # The caller holds the lecture coaching lock across both state and audit writes.
    previous = path.read_text(encoding="utf-8") if path.exists() else ""
    atomic_write_text(path, previous + json.dumps(payload, ensure_ascii=False) + "\n")

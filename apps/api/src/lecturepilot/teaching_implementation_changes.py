"""Exact private before/after evidence for AI-owned implementation repairs."""

from datetime import UTC, datetime

from lecturepilot.durable_files import atomic_write_json


def implementation_changes(before, after):
    previous = {target.id: target.model_dump(mode="json") for target in before.targets}
    changes = []
    for target in after.targets:
        old = previous.get(target.id, {})
        for field, value in target.model_dump(mode="json").items():
            if old.get(field) != value:
                changes.append(
                    {
                        "target_id": target.id,
                        "target_title": target.title,
                        "field": field,
                        "before": old.get(field),
                        "after": value,
                    }
                )
    return changes


def record_implementation_changes(path, before, after, reason):
    if before.revision == after.revision:
        return
    report = {
        "from_revision": before.revision,
        "to_revision": after.revision,
        "learning_intent_revision": after.learning_intent.revision,
        "source_revision": after.source_revision,
        "recorded_at": datetime.now(UTC).isoformat(),
        "reason": reason,
        "changes": implementation_changes(before, after),
    }
    atomic_write_json(
        path.parent / path.stem / "implementation-changes" / f"{after.revision}.json", report
    )

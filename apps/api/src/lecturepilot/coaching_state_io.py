from __future__ import annotations

from pydantic import ValidationError

from lecturepilot.coaching_state_models import DelayedReview

MAX_TURN_EVENTS = 200
MAX_RECENT_MESSAGES = 8


def migrate_coaching_payload(raw) -> dict:
    if not isinstance(raw, dict):
        return {}
    payload = dict(raw)
    messages = payload.get("messages")
    if isinstance(messages, list):
        payload["messages"] = messages[-MAX_RECENT_MESSAGES:]
    turns = payload.get("turns")
    if isinstance(turns, list):
        payload["turns"] = [_migrate_turn(turn) for turn in turns[-MAX_TURN_EVENTS:]]
    reviews = _valid_reviews(payload.get("delayed_reviews"))
    legacy = payload.pop("delayed_transfer", None)
    if isinstance(legacy, dict):
        try:
            review = DelayedReview.model_validate(legacy)
        except ValidationError:
            pass
        else:
            reviews.setdefault(review.gate_id, review.model_dump(mode="json"))
    payload["delayed_reviews"] = reviews
    return payload


def _valid_reviews(raw) -> dict:
    if not isinstance(raw, dict):
        return {}
    reviews = {}
    for gate_id, value in raw.items():
        try:
            review = DelayedReview.model_validate(value)
        except ValidationError:
            continue
        if gate_id == review.gate_id:
            reviews[gate_id] = review.model_dump(mode="json")
    return reviews


def _migrate_turn(raw):
    if not isinstance(raw, dict) or "attempt_kind" in raw:
        return raw
    migrated = dict(raw)
    if raw.get("transfer_attempt") is True:
        migrated["attempt_kind"] = "delayed_transfer"
    elif raw.get("independent_attempt") is True:
        migrated["attempt_kind"] = "independent"
    elif raw.get("support_before_attempt") is True:
        migrated["attempt_kind"] = "supported_retry"
    else:
        migrated["attempt_kind"] = "none"
    return migrated

from lecturepilot.canonical_digest import canonical_json_digest
from lecturepilot.course_learning_intent import digest as learning_intent_digest


PAYLOAD = {"b": [1, "Grüße", None], "a": {"z": 1.5, "y": True}}
# Pinned: stored revisions (learning maps, practice designs, design reports,
# learning intents, draft digests) must keep hashing to the same value.
PINNED = "1b6d97614322e3ae809b3c3a723d321e1603cd31c27503085e4f00f52bacb9e0"


def test_canonical_json_digest_is_pinned_and_key_order_independent() -> None:
    reordered = {"a": {"y": True, "z": 1.5}, "b": [1, "Grüße", None]}

    assert canonical_json_digest(PAYLOAD) == PINNED
    assert canonical_json_digest(reordered) == PINNED


def test_learning_intent_revisions_use_the_shared_canonical_digest() -> None:
    assert learning_intent_digest(PAYLOAD) == PINNED

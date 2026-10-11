"""Reject non-observable generated outcomes before professor review.

Stored and professor-edited goals keep the lenient model validator; this check only
steers new proposals, so existing approved intents remain readable.
"""

import re

_SUBJECT = re.compile(
    r"^(?:(?:the\s+)?(?:students?|learners?)\s+(?:should\s+|will\s+|can\s+)?(?:be\s+able\s+to\s+)?"
    r"|(?:die\s+)?(?:studierenden|lernenden)\s+(?:sollen\s+|können\s+)?)",
    re.IGNORECASE,
)
_VAGUE = (
    "understand",
    "know",
    "be familiar",
    "become familiar",
    "be aware",
    "appreciate",
    "learn about",
    "gain an understanding",
    "have an understanding",
    "verstehen",
    "kennen",
    "wissen",
    "vertraut",
    "ein verständnis",
)


def require_operational_outcomes(proposal) -> None:
    vague = [goal.id for goal in proposal.goals if _is_vague(goal.outcome)]
    if vague:
        raise ValueError(
            "Rewrite these outcomes to start with an observable operation such as identify, "
            "explain, calculate, derive, compare, trace or construct: " + ", ".join(vague)
        )


def _is_vague(outcome: str) -> bool:
    text = _SUBJECT.sub("", outcome.strip()).casefold()
    return any(text == verb or text.startswith(verb + " ") for verb in _VAGUE)

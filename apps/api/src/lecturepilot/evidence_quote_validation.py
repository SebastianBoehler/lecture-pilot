"""Reject trivial quotation anchors without claiming semantic correctness."""

import re


def substantive_quote(quote: str) -> bool:
    words = re.findall(r"\w+", quote, flags=re.UNICODE)
    return len(words) >= 2 or bool(re.search(r"\w\s*[=+*/<>−-]\s*\w", quote))


def learner_reasoning(answer: str) -> str:
    return re.sub(r"(?im)^Selected option:.*(?:\n|$)", "", answer)

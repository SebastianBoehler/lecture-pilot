"""Compact source-processing warnings for professors."""

import re

_OCR = re.compile(r"^OCR required but unavailable for (page|slide) (\d+)\b")


def compact_source_warnings(warnings: list[str], *, limit: int = 20) -> list[str]:
    """One line per OCR gap instead of one per page, so other notes stay visible."""
    numbers: dict[str, set[int]] = {}
    others: list[str] = []
    for warning in dict.fromkeys(warnings):
        match = _OCR.match(warning)
        if match:
            numbers.setdefault(match.group(1), set()).add(int(match.group(2)))
        else:
            others.append(warning)
    summaries = [
        f"OCR required but unavailable for {len(found)} {unit}"
        f"{'s' if len(found) != 1 else ''} ({_ranges(found)}); "
        f"the {unit} images were preserved and text on them was not extracted."
        for unit, found in sorted(numbers.items())
    ]
    return (summaries + others)[:limit]


def _ranges(values: set[int]) -> str:
    ordered = sorted(values)
    parts, start, previous = [], ordered[0], ordered[0]
    for value in ordered[1:] + [None]:
        if value is not None and value == previous + 1:
            previous = value
            continue
        parts.append(str(start) if start == previous else f"{start}–{previous}")
        if value is not None:
            start = previous = value
    return ", ".join(parts)

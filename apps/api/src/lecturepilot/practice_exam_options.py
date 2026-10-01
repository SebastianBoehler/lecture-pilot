"""Exact equivalence for standalone numeric choices, without evaluating expressions."""

from fractions import Fraction
import re


_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"


def has_equivalent_numeric_options(options: list[str]) -> bool:
    seen: set[Fraction] = set()
    for option in options:
        value = _numeric_value(option)
        if value is not None:
            if value in seen:
                return True
            seen.add(value)
    return False


def _numeric_value(option: str) -> Fraction | None:
    text = option.strip().strip("$").strip()
    fraction = re.fullmatch(rf"({_NUMBER})\s*/\s*({_NUMBER})", text)
    if fraction is None:
        fraction = re.fullmatch(rf"\\[dt]?frac\{{({_NUMBER})\}}\{{({_NUMBER})\}}", text)
    try:
        if fraction is not None:
            return Fraction(fraction[1]) / Fraction(fraction[2])
        if re.fullmatch(_NUMBER, text):
            return Fraction(text)
    except (ValueError, ZeroDivisionError):
        return None
    return None

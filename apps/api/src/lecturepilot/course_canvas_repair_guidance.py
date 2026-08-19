from __future__ import annotations


_BOUNDARIES = (
    "Repair boundaries: Edit only the requested blocks and address every listed defect in them. "
    "Use only supplied evidence; remove an unsupported statement instead of making it plausible. "
    "Preserve correct neighboring content, stable target ids, source notation, and answer meaning. "
    "Do not add new facts, sources, exercises, values, or pedagogical claims."
)

_EXAMPLES: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("unsupported", "not supported", "does not establish", "outside the supplied"),
        "Before: infer a useful consequence not stated in evidence. "
        "After: state the evidenced definition only, or remove the unsupported consequence.",
    ),
    (
        ("formula", "latex", "indexing", "mathemat", "equation", "partition"),
        "Before: repair a formula by simplifying away required notation. "
        "After: preserve every source variable and index, make domains and constraints explicit, "
        "and keep explanatory prose outside math blocks.",
    ),
    (
        ("checkpoint", "quiz", "assessment", "omitted", "self-contained", "options"),
        "Before: ask for a result using a table or options shown elsewhere. "
        "After: make the prompt answerable from evidence restated inside the task. "
        "Do not invent missing values; replace the task when evidence is incomplete.",
    ),
    (
        ("source_ref", "misattribute", "attribution"),
        "Before: attach every available source to the repaired claim. "
        "After: retain only the source reference that directly supports that claim.",
    ),
    (
        ("contradict", "inconsistent", "conflict"),
        "Before: silently choose one of two conflicting quantities. "
        "After: use the quantity supported in this section, or explicitly identify a documented "
        "source discrepancy without resolving it by invention.",
    ),
)


def repair_guidance(failure: str) -> str:
    normalized = failure.lower()
    selected = [
        example
        for keywords, example in _EXAMPLES
        if any(keyword in normalized for keyword in keywords)
    ][:2]
    if not selected:
        return _BOUNDARIES
    return f"{_BOUNDARIES} Selected micro-examples: {' '.join(selected)}"

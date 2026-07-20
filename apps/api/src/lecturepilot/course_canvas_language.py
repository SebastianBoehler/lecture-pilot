from __future__ import annotations


def canvas_language_instruction(output_language: str) -> str:
    if output_language not in {"de", "en"}:
        raise ValueError("Canvas language must be 'de' or 'en'.")
    label = "German" if output_language == "de" else "English"
    return (
        f"Write all natural-language canvas content in {label}, including the document title, "
        "section titles, explanations, lists, callouts, captions, checkpoints, quiz questions, "
        "and answer options. You may read and synthesize evidence in any language. Keep formulas, "
        "code, identifiers, file paths, and source citations unchanged."
    )

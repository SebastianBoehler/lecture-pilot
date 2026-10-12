from __future__ import annotations

import re

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.katex_commands import PORTABLE_KATEX_COMMANDS


_CONTROL_WORD_RE = re.compile(r"\\(?P<command>[A-Za-z]+)")
_DELIMITER_RE = re.compile(r"```|~~~|(?<!\\)\$|\\[()[\]]")
_MACRO_DIRECTIVE_RE = re.compile(
    r"\\(?:newcommand|renewcommand|providecommand|def|gdef|edef|xdef|let|input|include|"
    r"usepackage|documentclass)\b"
)
_ENVIRONMENT_RE = re.compile(r"\\(?:begin|end)\{(?P<environment>[A-Za-z*]+)\}")
_ALLOWED_ENVIRONMENTS = frozenset(
    {
        "aligned",
        "alignedat",
        "array",
        "Bmatrix",
        "bmatrix",
        "cases",
        "gathered",
        "matrix",
        "pmatrix",
        "smallmatrix",
        "Vmatrix",
        "vmatrix",
    }
)
_TEXT_ARGUMENT_RE = re.compile(
    r"\\(?:operatorname|text|textrm|textsf|texttt|mathrm|mathsf|mathtt|mathit)\*?\{[^{}]*\}"
)
_SCRIPT_IDENTIFIER_RE = re.compile(r"[_^]\{[A-Za-z0-9,+\-=&\s]*\}")
_PLAIN_PHRASE_RE = re.compile(r"(?<![\\.])\b[A-Za-z]{3,}\b(?:\s+|[-–—]\s*)\b[A-Za-z]{3,}\b(?!\.)")


def generated_math_instructions() -> str:
    return (
        "For every math block, return only one self-contained display expression as raw LaTeX "
        "from the portable KaTeX command subset. Do not add Markdown fences, dollar delimiters, "
        "document environments, preamble commands, or source-defined macros. "
        "Prefer copying an equation from the provided source math evidence instead of inventing "
        "or algebraically rewriting it. Rewrite source shorthands with standard commands, for "
        "example \\mathbb{N} for a number set and "
        "\\operatorname{loss} for a named operator. Put definitions, labels, and explanatory prose "
        "in adjacent paragraph or callout blocks; short in-equation labels may use \\text{...}. "
        "Keep a single equation as one expression. For a multi-line derivation, use "
        "\\begin{aligned} ... \\\\ ... \\end{aligned} inside the math block."
    )


def validate_document_math(document: CanvasDocument) -> None:
    for section in document.sections:
        validate_section_math(section)


def validate_section_math(section: CanvasSection) -> None:
    for block in section.blocks:
        if block.type != "math":
            continue
        error = math_block_error(block.text or "")
        if error:
            raise CanvasGenerationRepairableError(
                f"Math block {block.id} in {section.title} {error}",
                section_id=section.id,
                block_id=block.id,
            )


def math_block_error(value: str) -> str | None:
    formula = value.strip()
    if not formula:
        return "must contain a display expression."
    if _DELIMITER_RE.search(formula):
        return "must contain raw LaTeX without Markdown fences or math delimiters."
    if _MACRO_DIRECTIVE_RE.search(formula):
        return "cannot contain macro definitions or external TeX dependencies."
    if environment := _unsupported_environment(formula):
        return f"uses unsupported environment {environment}; use a raw expression or aligned math."
    if structure_error := _math_structure_error(formula):
        return structure_error
    commands = {match.group("command") for match in _CONTROL_WORD_RE.finditer(formula)}
    unsupported = sorted(commands - PORTABLE_KATEX_COMMANDS)
    if unsupported:
        names = ", ".join(f"\\{name}" for name in unsupported[:4])
        return f"uses unsupported or course-specific LaTeX commands: {names}."
    if _contains_plain_prose(formula):
        return "contains explanatory prose; move that text to a paragraph or callout block."
    return None


def _unsupported_environment(formula: str) -> str | None:
    for match in _ENVIRONMENT_RE.finditer(formula):
        environment = match.group("environment")
        if environment not in _ALLOWED_ENVIRONMENTS:
            return environment
    return None


def _math_structure_error(formula: str) -> str | None:
    brace_depth = 0
    for index, character in enumerate(formula):
        if character not in "{}" or _is_escaped(formula, index):
            continue
        if character == "{":
            brace_depth += 1
            continue
        brace_depth -= 1
        if brace_depth < 0:
            return "has unbalanced braces."
    if brace_depth:
        return "has unbalanced braces."

    environments: list[str] = []
    for match in _ENVIRONMENT_RE.finditer(formula):
        command = match.group(0).split("{", 1)[0]
        environment = match.group("environment")
        if command == r"\begin":
            environments.append(environment)
            continue
        if not environments:
            return f"has an unmatched \\end{{{environment}}} environment."
        expected = environments.pop()
        if environment != expected:
            return (
                f"closes environment {environment} while {expected} is still open; "
                "environment nesting must match."
            )
    if environments:
        return f"has an unmatched \\begin{{{environments[-1]}}} environment."
    return None


def _is_escaped(value: str, index: int) -> bool:
    preceding_backslashes = 0
    index -= 1
    while index >= 0 and value[index] == "\\":
        preceding_backslashes += 1
        index -= 1
    return preceding_backslashes % 2 == 1


def _contains_plain_prose(formula: str) -> bool:
    without_labels = _TEXT_ARGUMENT_RE.sub(" ", formula)
    without_environments = _ENVIRONMENT_RE.sub(" ", without_labels)
    without_commands = _CONTROL_WORD_RE.sub(" § ", without_environments)
    without_script_identifiers = _SCRIPT_IDENTIFIER_RE.sub(" ", without_commands)
    return bool(_PLAIN_PHRASE_RE.search(without_script_identifiers))

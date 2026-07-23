from __future__ import annotations

import re

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError


_PORTABLE_KATEX_COMMANDS = frozenset(
    """
    Alpha Beta Chi Delta Epsilon Eta Gamma Iota Kappa Lambda Mu Nu Omega Omicron Phi Pi Psi
    Rho Sigma Tau Theta Upsilon Xi Zeta alpha beta chi delta epsilon eta gamma iota kappa
    lambda mu nu omega omicron phi pi psi rho sigma tau theta upsilon xi zeta varepsilon
    varkappa varphi varpi varrho varsigma vartheta
    Bmatrix Delta Gamma Lambda Leftrightarrow Omega Phi Pi Psi Rightarrow Sigma Theta Upsilon
    Vmatrix Xi binom bmatrix begin cases matrix pmatrix end gathered aligned alignedat array
    smallmatrix vmatrix
    acute bar breve check dot ddot dddot ddddot grave hat mathring overline tilde underline
    vec widehat widetilde
    boldsymbol mathbb mathbf mathcal mathfrak mathit mathrm mathsf mathtt operatorname text
    textrm textsf texttt
    cfrac dfrac frac sqrt tfrac dbinom tbinom
    coprod iint iiint int oint prod sum bigcap bigcup bigodot bigoplus bigotimes bigsqcup biguplus
    lim liminf limsup max min sup inf limits nolimits mathop
    Pr arg cos cosh cot coth csc deg det dim exp gcd hom ker lg ln log prime sec sin sinh tan tanh
    arccos arcsin arctan
    partial nabla ell hbar imath jmath infty emptyset varnothing Re Im wp aleph top bot
    approx asymp cong equiv ge geq geqslant gt le leq leqslant lt neq ne propto sim simeq
    subset subseteq supset supseteq sqsubseteq sqsupseteq in ni notin mid parallel perp models
    prec preceq succ succeq
    cap cdot circ cup diamond div mp odot ominus oplus oslash otimes pm setminus smallsetminus
    sqcap sqcup star times triangleleft triangleright uplus vee wedge wr
    forall exists nexists neg land lor implies iff therefore because
    gets leftarrow mapsto rightarrow to Leftarrow Longleftarrow Longleftrightarrow Longrightarrow
    longleftarrow longleftrightarrow longmapsto longrightarrow leftrightarrow hookleftarrow
    hookrightarrow uparrow downarrow updownarrow Uparrow Downarrow Updownarrow
    left right middle langle rangle lceil rceil lfloor rfloor lvert rvert lVert rVert vert Vert
    big Big bigg Bigg bigl bigr Bigl Bigr biggl biggr Biggl Biggr
    dots cdots ddots ldots vdots
    displaystyle scriptstyle scriptscriptstyle textstyle quad qquad
    overset underset overbrace underbrace stackrel substack
    mod bmod pmod pod
    tag boxed cancel
    """.split()
)
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
_PLAIN_WORD_RE = re.compile(r"(?<!\\)\b[A-Za-z]{3,}\b")
_LEADING_LABEL_RE = re.compile(
    r"^(?P<label>[A-Za-z][A-Za-z0-9 ,.'’()/-]*[A-Za-z][ :]\s*)"
    r"(?P<formula>(?:\\[A-Za-z]+|[A-Za-z]\s*[_^(]).*)$",
    re.DOTALL,
)
_SOURCE_SHORTHANDS = (
    (re.compile(r"\\P\b"), r"\\Pr"),
    (re.compile(r"\\K\b"), "K"),
    (re.compile(r"\\Q\b"), "Q"),
    (re.compile(r"\\V\b"), "V"),
)
_GENERATED_MATH_WRAPPERS = (
    re.compile(
        r"^```(?:math|latex)?\s*(?P<formula>(?:(?!```).)*)\s*```$",
        re.DOTALL | re.IGNORECASE,
    ),
    re.compile(
        r"^~~~(?:math|latex)?\s*(?P<formula>(?:(?!~~~).)*)\s*~~~$",
        re.DOTALL | re.IGNORECASE,
    ),
    re.compile(r"^\$\$(?P<formula>.*?)\$\$$", re.DOTALL),
    re.compile(r"^\$(?P<formula>.*?)\$$", re.DOTALL),
    re.compile(r"^\\\[(?P<formula>.*?)\\\]$", re.DOTALL),
    re.compile(r"^\\\((?P<formula>.*?)\\\)$", re.DOTALL),
)
_DISPLAY_SEGMENT_RE = re.compile(
    r"\s*(?:```(?:math|latex)?\s*(?P<fence>.*?)\s*```|"
    r"~~~(?:math|latex)?\s*(?P<tilde>.*?)\s*~~~|"
    r"\$\$(?P<dollar>.*?)\$\$|\\\[(?P<bracket>.*?)\\\])\s*",
    re.DOTALL | re.IGNORECASE,
)


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


def normalize_generated_math(value: str) -> str:
    """Apply unambiguous display-math repairs before strict validation."""
    formula = value.strip()
    for wrapper in _GENERATED_MATH_WRAPPERS:
        if match := wrapper.fullmatch(formula):
            formula = match.group("formula").strip()
            break
    else:
        formula = _combine_display_segments(formula)
    formula = formula.replace(r"\[", "").replace(r"\]", "")
    formula = formula.replace(r"\(", "").replace(r"\)", "")
    for pattern, replacement in _SOURCE_SHORTHANDS:
        formula = pattern.sub(replacement, formula)
    match = _LEADING_LABEL_RE.match(formula)
    if not match or not _looks_like_expression(match.group("formula")):
        return formula
    label = match.group("label").replace("{", r"\{").replace("}", r"\}")
    return rf"\text{{{label}}}{match.group('formula')}"


def _combine_display_segments(value: str) -> str:
    """Join a model response made solely of display-delimited expressions."""
    matches = list(_DISPLAY_SEGMENT_RE.finditer(value))
    if len(matches) < 2:
        return value
    cursor = 0
    formulas: list[str] = []
    for match in matches:
        if value[cursor : match.start()].strip():
            return value
        formulas.append(
            (
                match.group("fence")
                or match.group("tilde")
                or match.group("dollar")
                or match.group("bracket")
                or ""
            ).strip()
        )
        cursor = match.end()
    if value[cursor:].strip() or any(not formula for formula in formulas):
        return value
    joined = r" \\ ".join(formulas)
    return rf"\begin{{gathered}}{joined}\end{{gathered}}"


def normalize_generated_math_block(value: str) -> tuple[str, str]:
    """Normalize model math and demote plain prose that was assigned the wrong block type."""
    formula = normalize_generated_math(value)
    block_type = (
        "paragraph"
        if _contains_plain_prose(formula) and not _looks_like_expression(formula)
        else "math"
    )
    return block_type, formula


def _looks_like_expression(value: str) -> bool:
    return bool(re.search(r"\\[A-Za-z]+|[=_^]|[A-Za-z]\s*\(", value))


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
    unsupported = sorted(commands - _PORTABLE_KATEX_COMMANDS)
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
    without_commands = _CONTROL_WORD_RE.sub(" ", without_environments)
    return bool(_PLAIN_WORD_RE.search(without_commands))

from __future__ import annotations

import re
from typing import Literal


AssessmentKind = Literal["checkpoint", "quiz"]

_QUESTION_WORDS = (
    "what",
    "which",
    "why",
    "how",
    "when",
    "where",
    "who",
    "does",
    "do",
    "is",
    "are",
    "can",
    "could",
    "should",
    "would",
    "was",
    "were",
    "was",
    "welche",
    "welcher",
    "welches",
    "warum",
    "wieso",
    "wie",
    "wann",
    "wo",
    "wer",
    "ist",
    "sind",
    "kann",
    "können",
    "soll",
)
_IMPERATIVE_WORDS = (
    "analyze",
    "apply",
    "calculate",
    "classify",
    "compare",
    "complete",
    "compute",
    "construct",
    "create",
    "demonstrate",
    "derive",
    "design",
    "determine",
    "discuss",
    "draw",
    "evaluate",
    "explain",
    "formulate",
    "give",
    "identify",
    "implement",
    "justify",
    "list",
    "map",
    "match",
    "name",
    "order",
    "outline",
    "prove",
    "propose",
    "select",
    "show",
    "state",
    "summarize",
    "test",
    "trace",
    "write",
    "analysiere",
    "beweise",
    "berechne",
    "beschreibe",
    "bestimme",
    "diskutiere",
    "entwirf",
    "ergänze",
    "erstelle",
    "evaluiere",
    "ordne",
    "erkläre",
    "formuliere",
    "führe",
    "identifiziere",
    "konstruiere",
    "leite",
    "liste",
    "nenne",
    "skizziere",
    "teste",
    "vergleiche",
    "wende",
)
_LABEL_PREFIX = re.compile(r"^(?:checkpoint|quiz|quality gate|lernzielkontrolle)\s*:", re.I)
_QUESTION = re.compile(
    rf"\b(?:{'|'.join(_QUESTION_WORDS)})\b[^?]*\?",
    re.I,
)
_CONTEXTLESS_REFERENCE = re.compile(
    r"\b(?:exercise sheet|the sheet|question\s+\d+|the source|this section|this slide|"
    r"übungsblatt|aufgabe\s+\d+|die quelle|dieser abschnitt|diese folie)\b",
    re.I,
)
_UNSTATED_CHECKPOINT_CHOICES = re.compile(
    r"^which\s+(?:statement|option|choice|task|example|probability assignment)\b",
    re.I,
)
_GENERIC_SCAFFOLD = (
    "as you would in an exam answer",
    "name the key idea, when it applies",
    "explain the key mechanism in",
    "write a concise exam-style answer",
    "wie in einer klausurantwort",
    "nenne die zentrale idee und wann sie gilt",
    "erkläre den zentralen mechanismus von",
)


def assessment_generation_instruction() -> str:
    return (
        "Assessment examples illustrate structure only; never copy their subject matter. "
        'VALID checkpoint: {"type":"checkpoint","text":"Given f(x)=2x+1, compute '
        'f(3) and show the substitution.","items":[],"caption":"Checkpoint",'
        '"answer_index":null}. '
        'VALID quiz: {"type":"quiz","text":"Which value equals f(3) when f(x)=2x+1?",'
        '"items":["5","6","7","8"],"caption":"Quick check","answer_index":2}. '
        'INVALID checkpoint text: "Checkpoint", "Check your understanding", or '
        '"Reflect on this section"; these do not state what evidence the learner must produce. '
        'Also invalid for a checkpoint: "Which statement/task/option is correct?" because '
        "checkpoint blocks have no choices; rewrite it to ask the learner to state, explain, "
        "calculate, or justify the source-backed answer. "
        "Every assessment must be standalone: it must be answerable from its own text without "
        "reading preceding blocks or opening the source. Restate every required value, formula, "
        "definition, table entry, and relevant code behavior inside the assessment text. "
        "Before returning JSON, verify every checkpoint starts with a direct question or an "
        "imperative such as calculate, compare, derive, explain, identify, or justify; verify "
        "every quiz ends in ? and has exactly one source-supported answer_index."
    )


def assessment_prompt_issue(text: str | None, kind: AssessmentKind) -> str | None:
    prompt = _normalize(text or "")
    if not prompt:
        return "needs non-empty text"
    if _LABEL_PREFIX.match(prompt):
        return "must keep labels in caption and start text with the task"
    if any(fragment in prompt.casefold() for fragment in _GENERIC_SCAFFOLD):
        return "must ask a specific source-grounded task instead of generic assessment scaffolding"
    if kind == "checkpoint" and _UNSTATED_CHECKPOINT_CHOICES.match(prompt):
        return "must not ask the learner to choose from statements, tasks, or options that are not stated"
    if _CONTEXTLESS_REFERENCE.search(prompt):
        return (
            "must be understandable without an exercise sheet, slide, or prior-question reference"
        )
    if kind == "quiz" and not _is_question(prompt):
        return "must contain one direct question ending in a question mark"
    if kind == "checkpoint" and not (_is_question(prompt) or _is_concrete_task(prompt)):
        return "must contain a direct question or concrete task"
    return None


def readiness_prompt(text: str | None, kind: AssessmentKind) -> str | None:
    prompt = _normalize(text or "")
    if _LABEL_PREFIX.match(prompt):
        match = _QUESTION.search(prompt)
        prompt = match.group(0) if match else ""
    if assessment_prompt_issue(prompt, kind):
        return None
    return prompt


def _is_question(prompt: str) -> bool:
    return prompt.endswith("?") and bool(_QUESTION.search(prompt))


def _is_concrete_task(prompt: str) -> bool:
    if _starts_with(prompt, _IMPERATIVE_WORDS):
        return True
    task_words = "|".join(_IMPERATIVE_WORDS)
    has_context_prefix = re.match(
        r"^(?:for|given|using|with|für|gegeben|anhand)\b",
        prompt,
        re.I,
    )
    return bool(has_context_prefix and re.search(rf"\b(?:{task_words})\b", prompt, re.I))


def _starts_with(prompt: str, words: tuple[str, ...]) -> bool:
    plain = re.sub(r"^[`*_#\s]+", "", prompt).casefold()
    return any(plain == word or plain.startswith(f"{word} ") for word in words)


def _normalize(value: str) -> str:
    return " ".join(value.split())

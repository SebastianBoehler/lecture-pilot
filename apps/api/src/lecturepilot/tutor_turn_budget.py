"""Tutor turn limits chosen from what the backend knows the turn is asked to do."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from lecturepilot.models import AgentTurnInput
from lecturepilot.raster_request_intent import is_explicit_raster_request

TUTOR_REQUEST_LIMIT = 4
# Four requests of a ~10-20k token prompt plus tool results; cached prefixes still count.
TUTOR_INPUT_TOKEN_LIMIT = 96_000
ASSESSMENT_MAX_TOKENS = 1_500
CHAT_MAX_TOKENS = 2_048
CHAT_OUTPUT_TOKEN_LIMIT = 4_096
WRITING_MAX_TOKENS = 8_192
WRITING_OUTPUT_TOKEN_LIMIT = 12_288

TutorTurnKind = Literal["assessment", "chat", "canvas_write"]

_WRITE_VERB = (
    r"append|add|create|generate|write|make|draw|sketch|build|produce|insert|extend|expand"
    r"|update|edit|rewrite|revise|summari[sz]e|note down|put|save"
    r"|f(?:ü|ue)g\w*|erstell\w*|erzeug\w*|schreib\w*|erg(?:ä|ae)nz\w*|aktualisier\w*"
    r"|(?:ü|ue)berarbeit\w*|zeichne\w*|notier\w*|mach\w*|fass\w*"
)
_WRITE_TARGET = (
    r"sections?|notes?|examples?|summary|summaries|cheat ?sheets?|infographics?|diagrams?"
    r"|tables?|charts?|graphs?|plots?|visuals?|visuali[sz]ations?|figures?|timelines?"
    r"|flashcards?|quiz(?:zes)?|canvas|explanations?|walkthroughs?|derivations?"
    r"|abschnitt\w*|notiz\w*|beispiel\w*|zusammenfassung\w*|spickzettel|diagramm\w*"
    r"|tabelle\w*|grafik\w*|skizze\w*|abbildung\w*|erkl(?:ä|ae)rung\w*|herleitung\w*"
)
_CANVAS_WRITE_REQUEST = re.compile(
    rf"\b(?:{_WRITE_VERB})\b[^.!?\n]{{0,80}}\b(?:{_WRITE_TARGET})\b"
    rf"|\b(?:{_WRITE_TARGET})\b[^.!?\n]{{0,40}}\b(?:{_WRITE_VERB}|hinzu\w*)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TutorTurnBudget:
    kind: TutorTurnKind
    max_tokens: int
    output_tokens_limit: int


def tutor_turn_budget(turn: AgentTurnInput, *, tools: bool) -> TutorTurnBudget:
    """Ordinary chat gets a small output cap; only explicit canvas writing gets the large one.

    The latest learner message, or a write offer in the previous assistant reply that the
    learner is now accepting, selects writing. A false positive only raises an upper bound.
    """
    if not tools:
        return TutorTurnBudget("assessment", ASSESSMENT_MAX_TOKENS, CHAT_OUTPUT_TOKEN_LIMIT)
    if canvas_write_requested(turn):
        return TutorTurnBudget("canvas_write", WRITING_MAX_TOKENS, WRITING_OUTPUT_TOKEN_LIMIT)
    return TutorTurnBudget("chat", CHAT_MAX_TOKENS, CHAT_OUTPUT_TOKEN_LIMIT)


def canvas_write_requested(turn: AgentTurnInput) -> bool:
    previous = next(
        (item.content for item in reversed(turn.recent_messages) if item.role == "assistant"),
        "",
    )
    return any(
        _CANVAS_WRITE_REQUEST.search(text) or is_explicit_raster_request(text)
        for text in (turn.message, previous)
        if text
    )


def tutor_quota_reservation(turn: AgentTurnInput, *, writing_turn_reservation: int) -> int:
    """Reserve the configured amount for writing turns and less by the smaller output cap."""
    budget = tutor_turn_budget(turn, tools=turn.checkpoint_gate_id is None)
    return max(
        budget.output_tokens_limit,
        writing_turn_reservation - (WRITING_OUTPUT_TOKEN_LIMIT - budget.output_tokens_limit),
    )

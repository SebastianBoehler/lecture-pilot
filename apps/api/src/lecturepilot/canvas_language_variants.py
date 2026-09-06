"""Reviewed teaching-only translations bound to one canonical publication."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_context import PublishedCanvasSnapshot

Language = Literal["de", "en"]
# Keep formulas, code, URLs and numeric literals outside translation authority.
_PROTECTED = re.compile(
    r"```[\s\S]*?```|`[^`]*`|\$\$[\s\S]*?\$\$|\$[^$\n]*\$|\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\]|(?<=\]\()[^)\n]+|https?://[^\s)]+|asset:[^\s)]+|\d+(?:[.,]\d+)*"
)
_TOKEN = re.compile(r"⟦LP\d+⟧")


class TeachingText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=400)
    text: str = Field(min_length=1, max_length=30000)


class TranslationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    texts: list[TeachingText] = Field(max_length=2000)


class LanguageVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Language
    publication_binding: str
    publication_version: int
    texts: list[TeachingText]
    digest: str
    published_at: str | None = None
    published_by: str | None = None


def teaching_texts(document: CanvasDocument) -> list[TeachingText]:
    result = [TeachingText(key="title", text=document.title)]
    for section in document.sections:
        result.append(TeachingText(key=f"section:{section.id}", text=section.title))
        for block in section.blocks:
            if block.type not in {"paragraph", "list", "callout", "asset", "video", "table"}:
                continue
            prefix = f"block:{section.id}:{block.id}"
            for field in ("text", "caption"):
                value = getattr(block, field)
                if value:
                    result.append(TeachingText(key=f"{prefix}:{field}", text=value))
            result.extend(
                TeachingText(key=f"{prefix}:item:{index}", text=text)
                for index, text in enumerate(block.items)
                if text
            )
    return result


def mask(text: str) -> tuple[str, list[str]]:
    protected: list[str] = []

    def replace(match):
        protected.append(match.group())
        return f"⟦LP{len(protected) - 1}⟧"

    if _TOKEN.search(text):
        raise ValueError("Teaching contains reserved translation markers.")
    return _PROTECTED.sub(replace, text), protected


def restore(text: str, original: str) -> str:
    _, protected = mask(original)
    if _TOKEN.findall(text) != [f"⟦LP{i}⟧" for i in range(len(protected))]:
        raise ValueError("Translation changed a protected formula, code or number marker.")
    # Reject invented math, code, links or numbers outside the preserved tokens.
    if _PROTECTED.search(_TOKEN.sub("", text)):
        raise ValueError("Translation added unapproved mathematical or source content.")
    restored = _TOKEN.sub(lambda m: protected[int(m.group()[3:-1])], text)
    if _operators(restored) != _operators(original):
        raise ValueError("Translation changed an arithmetic operator.")
    return restored


def _operators(text: str) -> list[str]:
    return re.findall(r"[+*/=^<>−]|(?<=\d)\s*-\s*(?=\d)|(?<!\w)-(?=\d)", text)


def binding(snapshot: PublishedCanvasSnapshot) -> str:
    return hashlib.sha256(snapshot.publication.model_dump_json().encode()).hexdigest()


def variant_digest(language: Language, base: str, texts: list[TeachingText]) -> str:
    return hashlib.sha256(
        json.dumps(
            [language, base, [t.model_dump() for t in texts]], sort_keys=True, ensure_ascii=False
        ).encode()
    ).hexdigest()


def prepare_variant(
    snapshot: PublishedCanvasSnapshot, language: Language, output: TranslationOutput
) -> LanguageVariant:
    originals = teaching_texts(snapshot.document)
    if [t.key for t in output.texts] != [t.key for t in originals]:
        raise ValueError("Translation must preserve the exact ordered teaching text identities.")
    texts = [
        TeachingText(key=src.key, text=restore(dst.text, src.text))
        for src, dst in zip(originals, output.texts, strict=True)
    ]
    base = binding(snapshot)
    return LanguageVariant(
        language=language,
        publication_binding=base,
        publication_version=snapshot.version,
        texts=texts,
        digest=variant_digest(language, base, texts),
    )


def validate_variant(variant: LanguageVariant, snapshot: PublishedCanvasSnapshot) -> None:
    if (
        variant.publication_binding != binding(snapshot)
        or variant.publication_version != snapshot.version
    ):
        raise ValueError(
            "The canonical publication changed. Generate and review the language again."
        )
    if variant.digest != variant_digest(
        variant.language, variant.publication_binding, variant.texts
    ):
        raise ValueError("Language variant integrity check failed.")
    originals = teaching_texts(snapshot.document)
    if [t.key for t in variant.texts] != [t.key for t in originals]:
        raise ValueError("Language teaching identities changed.")
    for src, dst in zip(originals, variant.texts, strict=True):
        if _PROTECTED.findall(src.text) != _PROTECTED.findall(dst.text) or _operators(
            src.text
        ) != _operators(dst.text):
            raise ValueError("Language variant changed protected teaching content.")


def publish_variant(
    variant: LanguageVariant, snapshot: PublishedCanvasSnapshot, digest: str, user_id: str
) -> LanguageVariant:
    validate_variant(variant, snapshot)
    if digest != variant.digest:
        raise ValueError("The reviewed language draft changed. Preview it again.")
    return variant.model_copy(
        update={"published_at": datetime.now(UTC).isoformat(), "published_by": user_id}
    )

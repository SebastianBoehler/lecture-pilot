from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from lecturepilot.agent_response_schema import lecture_schedule_response_format
from lecturepilot.course_canvas_json import parse_model_json
from lecturepilot.lecture_schedule import propose_lecture_schedule
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import LectureScheduleItem, LectureScheduleProposal, ProviderCapability, ProviderSettings
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry
from lecturepilot.source_bundle import SourceBundleFile

MAX_EVIDENCE_FILES = 80
MAX_EXCERPT_CHARS = 2400


class LectureScheduleModelClient(Protocol):
    async def complete_schedule(self, *, settings: ProviderSettings, messages: list[dict[str, str]]) -> dict:
        """Return a source-grounded full-course lecture schedule proposal."""


class LiteLLMScheduleClient:
    async def complete_schedule(self, *, settings: ProviderSettings, messages: list[dict[str, str]]) -> dict:
        try:
            from litellm import acompletion
        except ImportError as exc:
            raise ProviderConfigurationError(
                'litellm is not installed. Install the backend with the "agent" extra.'
            ) from exc
        try:
            response = await acompletion(
                model=settings.model,
                messages=messages,
                max_tokens=8000,
                temperature=0.1,
                response_format=lecture_schedule_response_format(),
            )
        except Exception as exc:
            raise ModelExecutionError("Lecture schedule model request failed.") from exc
        return parse_model_json(response.choices[0].message.content)


class LectureSchedulePlanner:
    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        model_client: LectureScheduleModelClient | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry.from_env()
        self.model_client = model_client or LiteLLMScheduleClient()

    async def propose_schedule(
        self,
        *,
        course_id: str,
        files: list[SourceBundleFile],
        roots: list[Path],
        first_lecture_date: date | None = None,
        requested_count: int | None = None,
    ) -> LectureScheduleProposal:
        settings = self.provider_registry.require_ready(
            [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        )
        messages = _schedule_messages(course_id, files, roots, first_lecture_date, requested_count)
        last_error: ProviderConfigurationError | None = None
        for _ in range(2):
            try:
                payload = await self.model_client.complete_schedule(settings=settings, messages=messages)
                return _complete_source_schedule(
                    _read_proposal(payload, course_id, files),
                    course_id=course_id,
                    files=files,
                    roots=roots,
                    first_lecture_date=first_lecture_date,
                    requested_count=requested_count,
                )
            except ProviderConfigurationError as exc:
                last_error = exc
                messages = [*messages, _repair_message(str(exc))]
        raise last_error or ProviderConfigurationError("Lecture schedule planner returned no usable proposal.")


def _schedule_messages(
    course_id: str,
    files: list[SourceBundleFile],
    roots: list[Path],
    first_lecture_date: date | None,
    requested_count: int | None,
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are the LecturePilot course-builder scheduling agent. Infer the "
                "course lecture structure from an uploaded source bundle. Use file names, "
                "LaTeX sections, Markdown headings, text excerpts, and media metadata as "
                "evidence. Return exactly one structured schedule with a top-level lectures "
                "array. Each lecture needs "
                "number, title, date, and material_path. Prefer concise real lecture topic "
                "titles over housekeeping frames such as plan, recap, feedback, note, or "
                "course thread. If a requested lecture count is absent, infer the count from "
                "the materials. Use weekly dates starting from the provided first lecture date. "
                "Set material_path to null when no single source file belongs to the lecture."
            ),
        },
        {
            "role": "user",
            "content": _source_evidence(course_id, files, roots, first_lecture_date, requested_count),
        },
    ]


def _repair_message(error: str) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            f"The previous schedule response violated the contract: {error}. "
            "Return exactly one structured schedule with this shape and no surrounding prose: "
            '{"lectures":[{"number":"01","title":"Topic title","date":"YYYY-MM-DD",'
            '"material_path":"Lecture01-eng.tex"}]}. Do not return a bare array.'
        ),
    }


def _source_evidence(
    course_id: str,
    files: list[SourceBundleFile],
    roots: list[Path],
    first_lecture_date: date | None,
    requested_count: int | None,
) -> str:
    seed = propose_lecture_schedule(
        course_id=course_id,
        files=files,
        roots=roots,
        first_lecture_date=first_lecture_date,
        requested_count=requested_count,
    )
    lines = [
        f"Course id: {course_id}",
        f"First lecture date: {first_lecture_date.isoformat() if first_lecture_date else date.today().isoformat()}",
        f"Requested count: {requested_count or 'infer from materials'}",
        "Deterministic file candidates, for reference only:",
    ]
    for lecture in seed.lectures:
        lines.append(
            f"- {lecture.number}: path={lecture.material_path}; "
            f"rough_title={lecture.title}; date={lecture.date}"
        )
    lines.append("\nSource bundle files and excerpts:")
    for item in sorted(files, key=_file_priority)[:MAX_EVIDENCE_FILES]:
        lines.append(_file_evidence(item, roots))
    return "\n".join(lines)


def _file_evidence(item: SourceBundleFile, roots: list[Path]) -> str:
    base = f"- path={item.path}; kind={item.kind}; size={item.size_bytes}"
    if item.kind not in {"latex", "markdown", "text", "json"}:
        return base
    path = _resolve_source(item.path, roots)
    if not path:
        return base
    text = path.read_text(encoding="utf-8", errors="ignore")
    return (
        f"{base}\n"
        f"  outline: {_outline(text, item.kind)}\n"
        f"  excerpt: {_compact_excerpt(text[:MAX_EXCERPT_CHARS])}"
    )


def _file_priority(item: SourceBundleFile) -> tuple[int, str]:
    kind_priority = {"latex": 0, "markdown": 1, "text": 2, "json": 3, "pdf": 4}.get(item.kind, 5)
    return (kind_priority, item.path.casefold())


def _resolve_source(relative_path: str, roots: list[Path]) -> Path | None:
    for root in roots:
        candidate = root / relative_path
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _compact_excerpt(text: str) -> str:
    return " ".join(line.strip() for line in text.splitlines() if line.strip())[:MAX_EXCERPT_CHARS]


def _outline(text: str, kind: str) -> str:
    if kind == "latex":
        titles = [
            _clean_title(match.group(1))
            for pattern in (r"\\section\{([^{}]+)\}", r"\\begin\{frame\}\{([^{}]+)\}", r"\\frametitle\{([^{}]+)\}")
            for match in re.finditer(pattern, text)
        ]
    elif kind == "markdown":
        titles = [_clean_title(match.group(1)) for match in re.finditer(r"^#{1,3}\s+(.+)$", text, re.MULTILINE)]
    else:
        titles = []
    unique = []
    for title in titles:
        if title and title.casefold() not in {item.casefold() for item in unique}:
            unique.append(title)
    return "; ".join(unique[:24]) or "no structured outline detected"


def _clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\\\\", " ")).strip(" -")


def _read_proposal(payload: dict, course_id: str, files: list[SourceBundleFile]) -> LectureScheduleProposal:
    raw_lectures = payload.get("lectures")
    if not isinstance(raw_lectures, list) or not raw_lectures:
        raise ProviderConfigurationError("Lecture schedule planner JSON must include lectures.")
    known_paths = {item.path for item in files}
    lectures: list[LectureScheduleItem] = []
    for index, raw in enumerate(raw_lectures[:80], start=1):
        if not isinstance(raw, dict):
            continue
        material_path = raw.get("material_path")
        if material_path and material_path not in known_paths:
            material_path = None
        try:
            lectures.append(
                LectureScheduleItem(
                    number=_schedule_number(str(raw.get("number") or f"{index:02d}")),
                    title=str(raw.get("title") or f"Lecture {index:02d}"),
                    date=raw.get("date"),
                    material_path=material_path,
                )
            )
        except ValidationError as exc:
            raise ProviderConfigurationError("Lecture schedule planner returned invalid lecture rows.") from exc
    if not lectures:
        raise ProviderConfigurationError("Lecture schedule planner returned no usable lectures.")
    return LectureScheduleProposal(
        course_id=course_id,
        lectures=lectures,
        source_paths=[lecture.material_path for lecture in lectures if lecture.material_path],
    )


def _complete_source_schedule(
    proposal: LectureScheduleProposal,
    *,
    course_id: str,
    files: list[SourceBundleFile],
    roots: list[Path],
    first_lecture_date: date | None,
    requested_count: int | None,
) -> LectureScheduleProposal:
    deterministic = propose_lecture_schedule(
        course_id=course_id,
        files=files,
        roots=roots,
        first_lecture_date=first_lecture_date,
        requested_count=requested_count,
    )
    if len(proposal.lectures) >= len(deterministic.lectures):
        return proposal
    by_number = {_lecture_key(lecture.number): lecture for lecture in proposal.lectures}
    merged = [by_number.get(_lecture_key(lecture.number), lecture) for lecture in deterministic.lectures]
    return LectureScheduleProposal(
        course_id=course_id,
        lectures=merged,
        source_paths=[lecture.material_path for lecture in merged if lecture.material_path],
    )


def _lecture_key(number: str) -> str:
    digits = re.sub(r"\D+", "", number)
    return str(int(digits)) if digits else number.strip().casefold()


def _schedule_number(number: str) -> str:
    digits = re.sub(r"\D+", "", number)
    return f"{int(digits):02d}" if digits else number.strip()

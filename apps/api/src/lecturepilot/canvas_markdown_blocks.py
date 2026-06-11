from __future__ import annotations

import re
from pathlib import Path

from lecturepilot.canvas_asset_refs import asset_markdown_target, parsed_asset_target
from lecturepilot.canvas_component_blocks import component_to_markdown, read_component_block
from lecturepilot.canvas_models import CanvasBlock


def block_to_markdown(block: CanvasBlock) -> str:
    header = f'<!-- block id="{block.id}" type="{block.type}" -->'
    if block.type == "asset":
        target = asset_markdown_target(block)
        caption = block.caption or block.asset_path or "Course figure"
        return f"{header}\n![{caption}]({target})"
    if block.type == "video":
        target = asset_markdown_target(block)
        caption = block.caption or "Course video"
        detail = f"\n{block.text}" if block.text else ""
        return f"{header}\n[{caption}]({target}){detail}"
    if block.type == "list":
        return f"{header}\n" + "\n".join(f"- {item}" for item in block.items)
    if block.type == "math":
        return f"{header}\n```math\n{block.text or ''}\n```"
    if block.type in {"checkpoint", "quiz"}:
        return f"{header}\n{_rich_container(block)}"
    if block.type == "table":
        return f"{header}\n{block.text or ''}"
    if block.type == "component":
        return f"{header}\n{component_to_markdown(block)}"
    if block.type == "callout":
        return f"{header}\n" + "\n".join(f"> {line}" for line in (block.text or "").splitlines())
    return f"{header}\n{block.text or ''}"


def read_blocks(
    body: str,
    *,
    section_id: str,
    course_id: str,
    lecture_id: str,
    components_dir: Path | None = None,
) -> list[CanvasBlock]:
    matches = list(_BLOCK_RE.finditer(body))
    if not matches:
        return _read_unmarked_blocks(
            body,
            section_id=section_id,
            course_id=course_id,
            lecture_id=lecture_id,
            components_dir=components_dir,
        )
    blocks = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        blocks.append(
            _read_block(
                match.group("id"),
                match.group("type"),
                body[start:end].strip(),
                section_id=section_id,
                course_id=course_id,
                lecture_id=lecture_id,
                components_dir=components_dir,
            )
        )
    return blocks


def type_suffix(block_type: str) -> str:
    return {
        "asset": "asset",
        "callout": "callout",
        "checkpoint": "checkpoint",
        "component": "component",
        "list": "list",
        "math": "math",
        "paragraph": "p",
        "quiz": "quiz",
        "table": "table",
        "video": "video",
    }[block_type]


def _read_unmarked_blocks(
    body: str,
    *,
    section_id: str,
    course_id: str,
    lecture_id: str,
    components_dir: Path | None,
) -> list[CanvasBlock]:
    blocks = []
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", body) if chunk.strip()]
    counters: dict[str, int] = {}
    for chunk in chunks:
        block_type = _infer_block_type(chunk)
        counters[block_type] = counters.get(block_type, 0) + 1
        block_id = f"{section_id}-{type_suffix(block_type)}-{counters[block_type]}"
        blocks.append(
            _read_block(
                block_id,
                block_type,
                chunk,
                section_id=section_id,
                course_id=course_id,
                lecture_id=lecture_id,
                components_dir=components_dir,
            )
        )
    return blocks


def _read_block(
    block_id: str,
    block_type: str,
    chunk: str,
    *,
    section_id: str,
    course_id: str,
    lecture_id: str,
    components_dir: Path | None,
) -> CanvasBlock:
    if block_type == "asset":
        match = _IMAGE_RE.search(chunk)
        target = match.group("target") if match else ""
        asset_path, asset_url = parsed_asset_target(
            target,
            course_id=course_id,
            lecture_id=lecture_id,
        )
        return CanvasBlock(
            id=block_id,
            type="asset",
            asset_path=asset_path,
            asset_url=asset_url,
            caption=match.group("caption") if match else asset_url,
        )
    if block_type == "video":
        caption, url, detail = _read_video(chunk)
        asset_path, asset_url = parsed_asset_target(url, course_id=course_id, lecture_id=lecture_id)
        return CanvasBlock(
            id=block_id,
            type="video",
            text=detail,
            asset_path=asset_path,
            asset_url=asset_url,
            caption=caption,
        )
    if block_type == "list":
        return CanvasBlock(id=block_id, type="list", items=_read_list_items(chunk))
    if block_type == "math":
        return CanvasBlock(id=block_id, type="math", text=_read_math(chunk))
    if block_type == "callout":
        return CanvasBlock(id=block_id, type="callout", text=_read_callout(chunk))
    if block_type == "checkpoint":
        caption, text = _read_rich_text(chunk, "checkpoint")
        return CanvasBlock(id=block_id, type="checkpoint", text=text, caption=caption)
    if block_type == "quiz":
        caption, text, items, answer_index = _read_quiz(chunk)
        return CanvasBlock(
            id=block_id,
            type="quiz",
            text=text,
            items=items,
            caption=caption,
            answer_index=answer_index,
        )
    if block_type == "component":
        return _read_component(block_id, chunk, components_dir=components_dir)
    if block_type == "table":
        return CanvasBlock(id=block_id, type="table", text=chunk.strip())
    if block_type != "paragraph":
        raise ValueError(f"Unsupported canvas block type: {block_type}")
    return CanvasBlock(id=block_id, type="paragraph", text=chunk.strip())


def _infer_block_type(chunk: str) -> str:
    rich = _rich_match(chunk)
    if rich and rich.group("kind") in {"checkpoint", "component", "quiz"}:
        return rich.group("kind")
    if _IMAGE_RE.search(chunk):
        return "asset"
    if chunk.startswith("```math"):
        return "math"
    if _is_markdown_table(chunk):
        return "table"
    if _youtube_link(chunk):
        return "video"
    if all(line.startswith("- ") for line in chunk.splitlines()):
        return "list"
    if all(line.startswith(">") for line in chunk.splitlines()):
        return "callout"
    return "paragraph"


def _rich_container(block: CanvasBlock) -> str:
    lines = [f":::{block.type}{f' {block.caption}' if block.caption else ''}", block.text or ""]
    for index, item in enumerate(block.items):
        marker = "[x] " if block.type == "quiz" and block.answer_index == index else ""
        lines.append(f"- {marker}{item}")
    return "\n".join([line for line in lines if line]).strip() + "\n:::"


def _read_rich_text(chunk: str, kind: str) -> tuple[str | None, str]:
    match = _rich_match(chunk)
    if not match or match.group("kind") != kind:
        return None, chunk.strip()
    return match.group("label").strip() or None, match.group("body").strip()


def _read_quiz(chunk: str) -> tuple[str | None, str, list[str], int | None]:
    caption, body = _read_rich_text(chunk, "quiz")
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    items: list[str] = []
    answer_index = None
    for line in lines:
        if not line.startswith("- "):
            continue
        item, is_correct = _read_quiz_item(line[2:].strip())
        if is_correct:
            answer_index = len(items)
        items.append(item)
    question = " ".join(line for line in lines if not line.startswith("- ")).strip()
    return caption, question, items, answer_index


def _read_quiz_item(item: str) -> tuple[str, bool]:
    match = re.match(r"\[(?P<checked>[xX ])]\s*(?P<text>.*)", item)
    if not match:
        return item, False
    return match.group("text").strip(), match.group("checked").lower() == "x"


def _read_component(block_id: str, chunk: str, *, components_dir: Path | None) -> CanvasBlock:
    label, body = _read_rich_text(chunk, "component")
    return read_component_block(block_id, label, body, components_dir=components_dir)


def _read_video(chunk: str) -> tuple[str, str, str | None]:
    match = _LINK_RE.search(chunk)
    url = _matched_url(match)
    caption = match.group("caption") if match and match.group("caption") else "Course video"
    detail = chunk.replace(match.group(0), "").strip() if match else None
    return caption, url, detail or None


def _youtube_link(chunk: str) -> bool:
    match = _LINK_RE.search(chunk)
    target = _matched_url(match)
    return "youtube.com/" in target or "youtu.be/" in target


def _matched_url(match: re.Match[str] | None) -> str:
    if not match:
        return ""
    return match.group("target") or match.group("bare") or ""


def _is_markdown_table(chunk: str) -> bool:
    lines = [line.strip() for line in chunk.splitlines() if line.strip()]
    return len(lines) >= 2 and "|" in lines[0] and bool(_TABLE_SEPARATOR_RE.fullmatch(lines[1]))


def _read_list_items(chunk: str) -> list[str]:
    return [line[2:].strip() for line in chunk.splitlines() if line.startswith("- ")]


def _read_math(chunk: str) -> str:
    match = _MATH_RE.search(chunk)
    return (match.group("formula") if match else chunk).strip()


def _read_callout(chunk: str) -> str:
    return "\n".join(line.removeprefix("> ").strip() for line in chunk.splitlines()).strip()


def _rich_match(chunk: str):
    return _RICH_RE.fullmatch(chunk.strip())


_BLOCK_RE = re.compile(r'<!--\s*block\s+id="(?P<id>[^"]+)"\s+type="(?P<type>[^"]+)"\s*-->')
_IMAGE_RE = re.compile(r"!\[(?P<caption>[^]]*)]\((?P<target>[^)]+)\)")
_LINK_RE = re.compile(r"\[(?P<caption>[^]]+)]\((?P<target>[^)]+)\)|(?P<bare>https?://\S+)")
_MATH_RE = re.compile(r"```math\s*(?P<formula>.*?)```", re.DOTALL)
_RICH_RE = re.compile(
    r":::(?P<kind>[a-zA-Z_-]+)\s*(?P<label>[^\n]*)\n(?P<body>.*?)\n?:::",
    re.DOTALL,
)
_TABLE_SEPARATOR_RE = re.compile(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?")

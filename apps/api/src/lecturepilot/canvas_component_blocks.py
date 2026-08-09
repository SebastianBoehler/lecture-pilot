from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from lecturepilot.canvas_component_catalog import component_data_from_payload
from lecturepilot.canvas_models import CanvasBlock, CanvasSection


def component_to_markdown(block: CanvasBlock, *, inline: bool = False) -> str:
    if inline:
        payload = json.dumps(_block_payload(block), indent=2, sort_keys=True)
        return f":::component\n{payload}\n:::"
    ref = block.component_ref or _default_component_ref(block)
    return f":::component {ref}\n:::"


def write_component_sources(section: CanvasSection, canvas_dir: Path) -> None:
    components_dir = canvas_dir / "components"
    for block in section.blocks:
        if block.type != "component":
            continue
        payload = _block_payload(block)
        component_path = _component_path(
            components_dir,
            block.component_ref or _default_component_ref(block),
        )
        component_path.parent.mkdir(parents=True, exist_ok=True)
        component_path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )


def read_component_block(
    block_id: str,
    label: str | None,
    body: str,
    *,
    components_dir: Path | None = None,
) -> CanvasBlock:
    payload, component_ref = _component_payload(label, body, components_dir)
    options = payload.get("options") if isinstance(payload.get("options"), list) else []
    items, option_ids, answer_index = _component_options(options)
    component_id = str(payload["id"])[:120]
    return CanvasBlock(
        id=block_id,
        type="component",
        component_id=component_id,
        component_type=str(payload["type"])[:120],
        component_ref=component_ref or _default_ref_for_id(component_id),
        component_version=int(payload["version"]),
        caption=str(payload.get("title") or _component_title(component_id))[:500],
        text=str(payload.get("prompt") or payload.get("text") or "").strip() or None,
        items=items,
        option_ids=option_ids,
        answer_index=answer_index,
        component_data=component_data_from_payload(payload.get("data")),
    )


def _component_payload(
    label: str | None,
    body: str,
    components_dir: Path | None,
) -> tuple[dict, str | None]:
    if body.strip():
        return _inline_payload(body), None
    if label and components_dir:
        path = _resolve_component_path(components_dir, label)
        return _load_component_file(path), path.relative_to(components_dir).as_posix()
    if label:
        raise ValueError(
            "Learner component blocks must contain their complete payload in Markdown."
        )
    raise ValueError("Canvas component block is missing its payload.")


def _inline_payload(body: str) -> dict:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = yaml.safe_load(body)
    if not isinstance(payload, dict):
        raise ValueError("Canvas component payload must be an object.")
    return _validated_component_payload(payload)


def _load_component_file(path: Path) -> dict:
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Canvas component payload must be an object.")
    return _validated_component_payload(payload)


def _validated_component_payload(payload: dict) -> dict:
    component_id = payload.get("id")
    component_type = payload.get("type")
    version = payload.get("version")
    if (
        not isinstance(component_id, str)
        or not component_id.strip()
        or not isinstance(component_type, str)
        or not component_type.strip()
        or type(version) is not int
        or version < 1
    ):
        raise ValueError(
            "Canvas component payload requires complete id, type, and integer version."
        )
    return payload


def _component_options(options: list[object]) -> tuple[list[str], list[str], int | None]:
    items: list[str] = []
    option_ids: list[str] = []
    answer_index = None
    for option in options[:26]:
        text, option_id, is_correct = _read_option(option, len(items))
        if not text:
            continue
        if is_correct:
            answer_index = len(items)
        items.append(text)
        option_ids.append(option_id)
    return items, option_ids, answer_index


def _read_option(option: object, index: int) -> tuple[str, str, bool]:
    if isinstance(option, dict):
        text = str(option.get("text") or option.get("label") or "").strip()
        option_id = str(option.get("id") or chr(65 + index)).strip()
        return text, option_id[:120], option.get("correct") is True
    return str(option).strip(), chr(65 + index), False


def _block_payload(block: CanvasBlock) -> dict:
    payload = {
        "id": block.component_id or block.id,
        "version": block.component_version or 1,
        "type": block.component_type or "unknown",
        "title": block.caption,
        "prompt": block.text,
        "options": [
            {
                "id": block.option_ids[index] if index < len(block.option_ids) else chr(65 + index),
                "text": item,
                "correct": block.answer_index == index,
            }
            for index, item in enumerate(block.items)
        ],
    }
    if block.component_data is not None:
        payload["data"] = block.component_data.model_dump(mode="json")
    return payload


def _resolve_component_path(components_dir: Path, ref: str) -> Path:
    if "/" not in ref and Path(ref).suffix == "":
        return _first_existing(components_dir, ref)
    return _component_path(components_dir, ref)


def _first_existing(components_dir: Path, component_id: str) -> Path:
    for suffix in (".yaml", ".yml", ".json"):
        candidate = _component_path(components_dir, f"{component_id}{suffix}")
        if candidate.exists():
            return candidate
    return _component_path(components_dir, f"{component_id}.yaml")


def _component_path(components_dir: Path, ref: str) -> Path:
    ref_path = Path(ref)
    if ref_path.is_absolute() or ".." in ref_path.parts:
        raise ValueError("Component references must stay inside the components directory.")
    path = components_dir / ref_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _default_component_ref(block: CanvasBlock) -> str:
    return _default_ref_for_id(block.component_id or block.id)


def _default_ref_for_id(component_id: str) -> str:
    return f"{component_id}.yaml"


def _component_title(component_id: str) -> str:
    stem = Path(component_id).stem
    words = [word for word in re.split(r"[-_\s]+", stem) if word]
    if len(words) > 1 and words[-1].lower() in {"component", "explorer", "process"}:
        words.pop()
    acronyms = {"ai", "api", "llm", "nlp", "ui", "ux"}
    title = " ".join(
        word.upper() if word.lower() in acronyms else word.capitalize() if index == 0 else word
        for index, word in enumerate(words)
    )
    return title or "Interactive component"

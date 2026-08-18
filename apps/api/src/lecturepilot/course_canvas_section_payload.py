from __future__ import annotations


def section_payload(payload: dict) -> dict:
    if isinstance(payload.get("section"), dict):
        payload = payload["section"]
    elif isinstance(payload.get("sections"), list) and payload["sections"]:
        first = payload["sections"][0]
        if isinstance(first, dict):
            payload = first
    if isinstance(payload.get("blocks"), list):
        return payload
    return {**payload, "blocks": _blocks_from_common_keys(payload)}


def _blocks_from_common_keys(payload: dict) -> list[dict]:
    blocks: list[dict] = []
    for key in ("summary", "content", "text", "paragraph"):
        if isinstance(payload.get(key), str) and payload[key].strip():
            blocks.append({"type": "paragraph", "text": payload[key]})
            break
    for key in ("key_points", "items", "bullets"):
        if isinstance(payload.get(key), list):
            blocks.append({"type": "list", "items": payload[key]})
            break
    for key in ("formula", "formulas", "math"):
        value = payload.get(key)
        if isinstance(value, str):
            blocks.append({"type": "math", "text": value})
        elif isinstance(value, list):
            blocks.extend({"type": "math", "text": item} for item in value if isinstance(item, str))
        if value:
            break
    for key in ("callout", "example", "infographic_brief"):
        if isinstance(payload.get(key), str) and payload[key].strip():
            blocks.append({"type": "callout", "text": payload[key]})
            break
    return blocks

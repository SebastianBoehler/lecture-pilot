from __future__ import annotations


HEADING_LABELS = {"title", "section_header"}


def docling_blocks(document: dict, *, suffix: str) -> list[dict]:
    blocks = []
    for item in document.get("texts", []):
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        locator = _locator(item, suffix=suffix)
        block = {
            "kind": "heading" if item.get("label") in HEADING_LABELS else "paragraph",
            "text": text,
            "locator": locator,
            "extraction": "native",
        }
        blocks.append(block)
    return blocks


def _locator(item: dict, *, suffix: str) -> dict:
    provenance = item.get("prov") or []
    page_number = provenance[0].get("page_no") if provenance else None
    locator = {}
    if page_number:
        locator["slide" if suffix in {".ppt", ".pptx", ".odp"} else "page"] = page_number
    if provenance and (bbox := provenance[0].get("bbox")):
        locator["bbox"] = [bbox[key] for key in ("l", "b", "r", "t")]
    return locator

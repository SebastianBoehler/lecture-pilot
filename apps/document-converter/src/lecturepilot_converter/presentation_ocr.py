from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from pathlib import Path

from lecturepilot_converter.ocr_page import process_ocr_page


MAX_OCR_SLIDES = 100
MAX_RENDERED_PIXELS = 20_000_000


def ocr_presentation_pages(rendered_pdf: Path, blocks: list[dict]) -> tuple[list[dict], list[str]]:
    import pypdfium2 as pdfium

    native_text: dict[int, list[str]] = defaultdict(list)
    for block in blocks:
        slide = block.get("locator", {}).get("slide")
        if slide and block.get("text"):
            native_text[int(slide)].append(str(block["text"]))
    document = pdfium.PdfDocument(rendered_pdf)
    ocr_blocks = []
    warnings = []
    try:
        for index in range(min(len(document), MAX_OCR_SLIDES)):
            page = document[index]
            width, height = map(float, page.get_size())
            text = "\n".join(native_text[index + 1])
            image = _render_png(page, width=width, height=height)
            result = process_ocr_page(
                image=image,
                native_text=text,
                raster_ratio=1.0,
                page=index + 1,
                width=width,
                height=height,
            )
            if result.extraction == "ocr":
                ocr_blocks.append(
                    {
                        "kind": "paragraph",
                        "text": result.text,
                        "locator": {
                            "slide": index + 1,
                            "bbox": list(result.locator.bbox),
                        },
                        "extraction": "ocr",
                    }
                )
            elif result.warning:
                warnings.append(
                    f"OCR required but unavailable for slide {index + 1}; "
                    "the rendered slide was preserved."
                )
    finally:
        document.close()
    return ocr_blocks, warnings


def _render_png(page, *, width: float, height: float) -> bytes:
    scale = min(2.0, (MAX_RENDERED_PIXELS / max(1.0, width * height)) ** 0.5)
    bitmap = page.render(scale=scale)
    output = BytesIO()
    try:
        bitmap.to_pil().save(output, format="PNG")
    finally:
        bitmap.close()
    return output.getvalue()

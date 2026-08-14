# Document OCR quality gate

LecturePilot uses OCR only when deterministic triage finds inadequate native
text on a raster-bearing PDF page or presentation slide. OCR output is marked
as derived evidence and never replaces the original rendered page.

## Private corpus

Keep evaluation images outside Git. Create a private JSON manifest with entries
for all six strata:

- German and English prose
- lecture slides
- formulas
- source code
- tables and charts
- degraded scans or handwriting

Each entry needs `id`, `category`, `image`, and `expected_text`. `image` is
resolved relative to the private manifest. Optional `required_terms` provide
case-sensitive structural checks. Do not use real professor pages without
permission; the committed repository contains no evaluation source material.

```json
{
  "samples": [
    {
      "id": "de-prose-01",
      "category": "prose",
      "image": "pages/de-prose-01.png",
      "expected_text": "Private ground-truth transcription",
      "required_terms": ["Private"]
    }
  ]
}
```

Run the PaddleOCR-VL service separately, then execute:

```bash
python scripts/benchmark_document_ocr.py \
  --manifest /absolute/private/corpus.json \
  --base-url http://127.0.0.1:8080 \
  --output /absolute/private/paddleocr-vl-1.6.json
```

The report includes per-sample character error rate, missing required terms,
latency, output length, and per-stratum summaries. Before enabling production
OCR, manually score reading order, formulas, and table structure, then record
peak RAM or VRAM and p50/p95 page latency on the intended worker. A model does
not pass merely because prose CER is low.

OCR remains optional until the private corpus and deployment-capacity gates
pass. When unavailable, LecturePilot preserves the page image and reports the
specific page or slide requiring OCR instead of inventing text.

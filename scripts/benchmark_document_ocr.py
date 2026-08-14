#!/usr/bin/env python3
from __future__ import annotations

import argparse
from base64 import b64encode
from collections import defaultdict
import json
from pathlib import Path
from statistics import median
from time import perf_counter
from urllib.request import Request, urlopen


MAX_TEXT_CHARS = 20_000


def main() -> None:
    arguments = _arguments()
    manifest_path = arguments.manifest.resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    samples = payload.get("samples")
    if not isinstance(samples, list) or not samples:
        raise SystemExit("The OCR manifest must contain at least one sample.")
    results = [
        _evaluate(sample, manifest_path.parent, arguments.base_url.rstrip("/"))
        for sample in samples
    ]
    report = {
        "schema_version": 1,
        "model": "PaddleOCR-VL-1.6",
        "samples": results,
        "strata": _strata(results),
        "overall": _summary(results),
    }
    arguments.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark a private OCR page corpus.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _evaluate(sample: dict, root: Path, base_url: str) -> dict:
    sample_id = _required_text(sample, "id")
    category = _required_text(sample, "category")
    expected = _required_text(sample, "expected_text")[:MAX_TEXT_CHARS]
    image_path = (root / _required_text(sample, "image")).resolve()
    if root not in image_path.parents or not image_path.is_file():
        raise SystemExit(f"Unsafe or missing image for {sample_id}.")
    started = perf_counter()
    actual = _request_ocr(base_url, image_path.read_bytes())[:MAX_TEXT_CHARS]
    elapsed = perf_counter() - started
    required_terms = sample.get("required_terms", [])
    if not isinstance(required_terms, list) or not all(
        isinstance(term, str) for term in required_terms
    ):
        raise SystemExit(f"Invalid required_terms for {sample_id}.")
    return {
        "id": sample_id,
        "category": category,
        "character_error_rate": round(_character_error_rate(expected, actual), 6),
        "missing_required_terms": [
            term for term in required_terms if term not in actual
        ],
        "seconds": round(elapsed, 4),
        "output_chars": len(actual),
    }


def _request_ocr(base_url: str, image: bytes) -> str:
    request = Request(
        f"{base_url}/layout-parsing",
        data=json.dumps(
            {
                "file": b64encode(image).decode("ascii"),
                "fileType": 1,
                "returnMarkdownImages": False,
                "visualize": False,
                "restructurePages": False,
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=120) as response:
        payload = json.load(response)
    results = payload["result"]["layoutParsingResults"]
    if payload.get("errorCode") != 0 or len(results) != 1:
        raise RuntimeError("PaddleOCR returned an invalid single-page response.")
    return str(results[0]["markdown"]["text"])


def _character_error_rate(expected: str, actual: str) -> float:
    if not expected:
        return 0.0 if not actual else 1.0
    previous = list(range(len(actual) + 1))
    for expected_char in expected:
        current = [previous[0] + 1]
        for index, actual_char in enumerate(actual, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[index] + 1,
                    previous[index - 1] + (expected_char != actual_char),
                )
            )
        previous = current
    return previous[-1] / len(expected)


def _strata(results: list[dict]) -> dict:
    grouped = defaultdict(list)
    for result in results:
        grouped[result["category"]].append(result)
    return {category: _summary(items) for category, items in sorted(grouped.items())}


def _summary(results: list[dict]) -> dict:
    latency = sorted(result["seconds"] for result in results)
    return {
        "samples": len(results),
        "mean_character_error_rate": round(
            sum(result["character_error_rate"] for result in results) / len(results), 6
        ),
        "p50_seconds": round(median(latency), 4),
        "p95_seconds": round(
            latency[min(len(latency) - 1, int(len(latency) * 0.95))], 4
        ),
        "samples_missing_required_terms": sum(
            bool(result["missing_required_terms"]) for result in results
        ),
    }


def _required_text(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"OCR manifest field {key} must be non-empty text.")
    return value


if __name__ == "__main__":
    main()

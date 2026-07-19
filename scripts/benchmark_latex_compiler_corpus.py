from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import tempfile
import time

import fitz

from lecturepilot.latex_compilation_client import (
    LatexCompilationError,
    compile_latex_deck,
)
from lecturepilot.latex_dependency_bundle import resolve_latex_compiler_inputs
from lecturepilot.source_index import refresh_course_source_index


DEFAULT_PATTERN = r"(?:Lecture|tutorial)\d+-eng\.tex"
fitz.TOOLS.mupdf_display_errors(False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile a private LaTeX corpus without recording its contents."
    )
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--compiler-url", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    args = parser.parse_args()

    source_root = args.source_root.resolve(strict=True)
    os.environ["LECTUREPILOT_LATEX_COMPILER_URL"] = args.compiler_url
    args.output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lecturepilot-corpus-index-") as temporary:
        index = refresh_course_source_index(
            course_id="private-corpus",
            uploads_dir=source_root,
            index_path=Path(temporary) / "source-index.json",
        )
        source_paths = sorted(
            item.path
            for item in index.files
            if item.kind == "latex" and re.fullmatch(args.pattern, item.path)
        )
        results = [
            _compile_one(source_root, index, source_path, args.output_root)
            for source_path in source_paths
        ]

    print(json.dumps({"compiler_url": args.compiler_url, "results": results}, indent=2))


def _compile_one(source_root, index, source_path: str, output_root: Path) -> dict:
    inputs = resolve_latex_compiler_inputs(
        source_root=source_root,
        source_index=index,
        source_path=source_path,
    )
    started = time.monotonic()
    result = {
        "source": source_path,
        "input_files": len(inputs),
        "input_bytes": sum(item.size_bytes for item in inputs),
    }
    try:
        output = compile_latex_deck(
            source_root=source_root,
            inputs=inputs,
            source_path=source_path,
            output_root=output_root,
            lecture_id=Path(source_path).stem,
        )
        with fitz.open(output) as document:
            result.update(
                status="ok",
                pages=len(document),
                page_sizes=[
                    [round(page.rect.width, 3), round(page.rect.height, 3)]
                    for page in document
                ],
                pdf_bytes=output.stat().st_size,
                output=str(output),
            )
    except LatexCompilationError as exc:
        result.update(status="failed", error_code=exc.code)
    result["seconds"] = round(time.monotonic() - started, 3)
    return result


if __name__ == "__main__":
    main()

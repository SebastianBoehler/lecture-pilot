# Tectonic compiler parity evidence

Recorded on 2026-07-19 on ARM64. The initial comparison used the existing TeX Live
compiler image with the pinned Tectonic 0.16.9 image through the real isolated
HTTP service. Both services ran read-only with one CPU. The private corpus was
indexed and dependency-bundled through the same API path used by LecturePilot;
source contents were not written to the report.

Tectonic is now the deployed compiler. The results below are dated migration
evidence, while [`latex-compilation.md`](latex-compilation.md) is the current
runtime contract.

## Result

| Check                     |      TeX Live |      Tectonic |
| ------------------------- | ------------: | ------------: |
| Corpus documents compiled |         23/27 |         23/27 |
| Successful page counts    |      baseline |   23/23 equal |
| Maximum page-size delta   |      baseline |      0.003 pt |
| Median successful compile |       2.966 s |       4.498 s |
| Total corpus time         |      84.928 s |     125.824 s |
| ARM64 image size          | 759,608,030 B | 227,875,862 B |

The Tectonic image is 70.0% smaller, but this cold service-level corpus run is
about 52% slower at the median. The migration is therefore a distribution,
reproducibility, and attack-surface win, not a compile-speed win.

A follow-up integration run on 2026-07-20 fixed dependency lookup for graphic
basenames containing decimal-like suffixes such as `plot_0.35_data`. Tectonic
then compiled 25/27 documents, including the two Lecture 08 variants that had
previously been bundled without their real `.pdf` extensions. The remaining
two failures were already present in the TeX Live baseline and are invalid or
missing-dependency professor sources rather than engine regressions.

All 23 successful outputs have the same page count. Extracted-text similarity
is at least 99.29% per document, with a 99.91% median. Manual inspection of
representative lecture and tutorial pages found no missing content or visible
layout regression. Their mean grayscale raster deltas were 0.06%, 0.79%, and
0.70%; PDF bytes are not expected to be identical across pdfTeX and XeTeX.

The baseline's other two failures reference invalid or missing local course
dependencies. A matching uploaded PDF remains authoritative for such courses.

## Format and edge-case matrix

The committed synthetic matrix verifies expected behavior without private
course data:

| Scenario                                                                   | Expected result       |
| -------------------------------------------------------------------------- | --------------------- |
| Nested Beamer, root/local inputs, custom macros, Unicode, mixed-case image | compile               |
| Article with theorem, formulas, German, and long table                     | compile               |
| Nested report with local and root inputs                                   | compile               |
| Book with contents, chapter, and section                                   | compile               |
| Uploaded custom `.cls`                                                     | compile               |
| BibTeX with uploaded `.bib`                                                | compile               |
| Declared Latin-1 source                                                    | transcode and compile |
| Shell escape                                                               | reject                |
| Unseeded private package                                                   | reject                |
| Raw SVG requiring conversion                                               | reject                |

The image also seeds 10pt, default 11pt, and 12pt Beamer resources, common
Computer Modern font paths found by the corpus, article/report/book classes,
BibTeX, German/English Unicode, tables, algorithms, listings, TikZ, PGFPlots,
and the packages used by the current professor corpus. The build proves every
seed compiles again with the network-independent `--only-cached` flag.

## Compatibility boundary

This does not provide every possible LaTeX workflow:

- Tectonic is XeTeX-derived, so low-level pdfTeX primitives or font assumptions
  can render differently or require a small adapter.
- Runtime package downloads are disabled. A newly encountered CTAN package must
  be added to the build seed and corpus-tested before release.
- Shell escape, `minted`-style external execution, and raw SVG conversion stay
  disabled for untrusted uploads.
- BibTeX is supported; Biber and host-installed system fonts are not included.
- Small typography and PDF-metadata differences are expected even when pages
  are visually equivalent.

The implementation compensates for practical source-layout differences without
weakening `--untrusted`: it creates bounded temporary aliases for course-root
dependencies and case-only filename mismatches, statically disables multimedia,
forces Beamer handout mode, and normalizes explicitly declared legacy encodings.

## Recommendation

Adopt Tectonic behind the existing compiler-service contract. Do not fork
Tectonic yet. The corpus reached exact coverage parity with image seeding and a
small Python adapter; a fork would add a long-term engine-maintenance obligation
without improving current support. Reconsider a fork only if a representative
course exposes an engine-level incompatibility that cannot be handled by a
local style/class, safe adapter, or additional bundle seed.

Reproduce the public edge matrix with:

```bash
python scripts/verify_tectonic_compatibility.py \
  --compiler-url http://127.0.0.1:8081
```

Run the private corpus benchmark with:

```bash
PYTHONPATH=apps/api/src python scripts/benchmark_latex_compiler_corpus.py \
  --source-root /absolute/path/to/course \
  --compiler-url http://127.0.0.1:8081 \
  --output-root /tmp/lecturepilot-tectonic-corpus
```

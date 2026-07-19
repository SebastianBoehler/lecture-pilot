# LaTeX compilation

TeX-only slide previews run outside the credential-bearing API process. Build
and start the isolated compiler in another terminal before the API:

```bash
docker build -f apps/latex-compiler/Dockerfile -t lecturepilot-latex-compiler .
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,nodev,size=768m \
  --cap-drop ALL --security-opt no-new-privileges:true --pids-limit 64 \
  --memory 1g --cpus 1 -p 127.0.0.1:8081:8080 lecturepilot-latex-compiler
```

Point the API process at the compiler before starting Uvicorn:

```bash
export LECTUREPILOT_LATEX_COMPILER_URL=http://127.0.0.1:8081
```

A matching uploaded PDF, including a numbered handout such as
`Lecture02-handout.pdf`, remains authoritative and skips compilation. If the
service or a dependency is unavailable, generation continues from parsed TeX
and asks the professor to fix the source or upload the PDF.

The image pins Tectonic 0.16.9 and the `tlextras-2022.0r0` bundle. Its build
compiles representative Beamer, article, report, book, and BibTeX documents,
then proves the same documents compile with `--only-cached`. Runtime compilation
also uses `--only-cached --untrusted`, so uploaded sources cannot fetch packages
or invoke shell commands.

The adapter preserves course layouts commonly lost in a direct engine swap:

- nested main files can resolve both local and course-root support files;
- case-only filename mistakes are reconciled inside the temporary compile tree;
- declared Latin-1 and Windows-1252 TeX sources are transcoded to UTF-8;
- local `.sty` and `.cls` files and BibTeX `.bib`/`.bst` files are accepted;
- Beamer is forced into handout mode and multimedia controls become static.

The image is intentionally a corpus-seeded LaTeX distribution, not all of CTAN.
An unseeded package requires an image rebuild. Raw SVG conversion, shell-escape
workflows such as `minted`, Biber, and host-installed fonts are not provided.
Upload a preconverted PDF/image or a matching authoritative PDF when a course
depends on one of those workflows.

Run the synthetic compatibility matrix against a local service with:

```bash
python scripts/verify_tectonic_compatibility.py \
  --compiler-url http://127.0.0.1:8081
```

For a private professor corpus, use `scripts/benchmark_latex_compiler_corpus.py`.
It reports paths, dependency counts, page geometry, output size, and timing, but
does not record source contents. See [tectonic-parity.md](tectonic-parity.md) for
the migration evidence and remaining compatibility boundary.

Production uses the internal-only compiler service defined in
`deploy/compose.yml`; see [self-hosting.md](self-hosting.md) for its isolation
and resource boundaries.

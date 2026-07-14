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

Production uses the internal-only compiler service defined in
`deploy/compose.yml`; see [self-hosting.md](self-hosting.md) for its isolation
and resource boundaries.

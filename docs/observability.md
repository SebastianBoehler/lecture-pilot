# Observability

LecturePilot uses a no-op observability layer by default. Production Compose
enables metadata-only JSON spans in the API process logs:

```bash
export LECTUREPILOT_OBSERVABILITY=logging
export LECTUREPILOT_TRACE_CONTENT=metadata
```

The logging backend records only allowlisted operational metadata. It never
records prompts, responses, exception messages, credentials, source content,
raw request URLs, query strings, or asset paths. Every HTTP request receives a
server-generated `X-Request-ID`; request events use the FastAPI route template
instead of browser-controlled path values. Successful `/health` and `/ready`
probes are suppressed, while failed probes remain visible.

Workflow spans emit a start event followed by a finish event with status and
latency. A start without a finish therefore identifies interrupted or hung
work. Production also records categorized login, logout, session rejection,
university-sync, course-schedule, model, tool, and canvas-generation metadata.

Compose persists API and compiler JSONL metadata in separate named volumes.
Each service rotates at UTC midnight and retains the current file plus 13
daily files. When these file paths are configured, the metadata loggers do not
also copy the same events into the container stdout stream; the rotating JSONL
files are canonical. Inspect them without copying course content into logs:

```bash
docker compose -f deploy/compose.yml exec -T api \
  tail -n 200 /app/logs/api-metadata.jsonl
docker compose -f deploy/compose.yml exec -T latex-compiler \
  tail -n 200 /app/logs/compiler-metadata.jsonl
```

Uvicorn's duplicate access log is disabled in the production image; the safe
request events are the canonical API access diagnostics.

To trace agent turns, model calls, low-level workspace tools, canvas writes,
and quality-gate decisions into a self-hosted MLflow tracking server, install
the optional backend dependency and enable it:

```bash
pip install -e "apps/api[observability]"
export LECTUREPILOT_OBSERVABILITY=mlflow
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
export MLFLOW_EXPERIMENT=lecturepilot-dev
```

Trace content defaults to metadata only. Set
`LECTUREPILOT_TRACE_CONTENT=redacted` to add hashed prompt/response payloads, or
`LECTUREPILOT_TRACE_CONTENT=full` only in local/private debugging sessions where
course and student text may be stored in the tracing backend.

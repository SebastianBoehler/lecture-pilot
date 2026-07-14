# Observability

LecturePilot uses a no-op observability layer by default. Production Compose
enables metadata-only JSON spans in the API process logs:

```bash
export LECTUREPILOT_OBSERVABILITY=logging
export LECTUREPILOT_TRACE_CONTENT=metadata
```

The logging backend records only allowlisted operational metadata. It never
records prompts, responses, exception messages, credentials, source content,
or asset paths.

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

# Self-Hosting Notes

LecturePilot is intended to be deployable in a university setting without
per-user containers or arbitrary host filesystem access.

## Minimal Deployment

```txt
web container
api/agent container
Postgres
S3-compatible object storage
```

Redis or a queue can be added when ingestion jobs become long-running.
The starter Compose file now includes a Postgres container as the persistence
checkpoint, but the application still needs migrations and DB-backed auth,
courses, memberships, and enrollments before production rollout.

## Postgres

The Compose stack uses the lightweight `postgres:16-alpine` image with a named
volume. For staging or production, override `LECTUREPILOT_POSTGRES_PASSWORD`
and back up the `lecturepilot-postgres` volume.

## File Limits

Recommended defaults:

```txt
Markdown/text: 5 MB
JSON artifacts: 2 MB
Images: 20 MB
PDF course source: 100 MB
Per-learner quota: 500 MB to 1 GB
```

The current `WorkspacePolicy` enforces generated-file limits in the API.

## Secrets

Model provider keys stay server-side. Browser code must not receive provider
keys or university credentials.

## Course Materials

Store official source material as versioned, read-only course seed files.
Learner annotations, progress, summaries, and generated artifacts live in a
private overlay.

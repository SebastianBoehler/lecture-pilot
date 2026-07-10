# Self-hosting notes

LecturePilot is designed for one hardened shared service, not per-user containers or arbitrary host
filesystem access. The checked-in Compose stack is a staging starter; it is not approval to deploy
the live VM.

## Runtime layout

```txt
internet -> Caddy HTTPS gateway -> web and /api proxy
                                -> non-root FastAPI/agent service
FastAPI -> internal Postgres
FastAPI -> persisted /app/storage volume
```

Only the gateway publishes ports 80 and 443. API, web, migration, and database ports remain on the
Compose network. The migration service must finish before the API starts.

## Required configuration

Set at least:

- `LECTUREPILOT_DOMAIN`
- a strong `LECTUREPILOT_POSTGRES_PASSWORD`
- the required model/image provider keys
- the university-wrapper configuration needed by `tue-api-wrapper`
- an explicit server model allowlist

Production forces database session auth, schema verification, trusted Host and Origin lists, HSTS,
bounded material processing, quotas, and the persisted `/app/storage` root. Provider and university
credentials stay server-side. Professor passwords are stored as Argon2id hashes, and production web
builds omit both development demo-login buttons.

Validate without starting the live stack:

```bash
docker compose -f deploy/compose.yml config
docker compose -f deploy/compose.yml build
```

The API image runs as UID 10001 with a read-only root, dropped capabilities, a temporary `/tmp`, and
CPU/memory/process limits. Gateway, web, and database use patched derived images recorded in
`deploy/`.

## Storage and recovery

Postgres stores identity, roles, sessions, ownership, enrollments, audit, and quota state. The named
storage volume contains course and learner files. They form one recovery unit and must be backed up,
restored, encrypted, and versioned together. Follow `docs/security-operations.md`; a successful
restore rehearsal is a live-release gate.

## Upload and parser limits

`WorkspacePolicy` applies per-type byte limits. Uploads stream to quarantine, validate signature and
MIME, reject active SVG and unsafe paths, and promote atomically. PDF extraction and rendering run in
bounded worker processes with page, pixel, CPU, memory, file, and timeout limits.

## Current release blockers

Do not host publicly until all blockers in `security_best_practices_report.md` are closed. In
particular, student Alma/ILIAS identifier matching across representative accounts, disposable TLS
staging, backup restore, retention, deletion, privacy notice, and provider/subprocessor review remain
unverified or incomplete. The pinned `tue-api-wrapper==0.2.3` and Pillow 12.3 dependency set passes
the current Python audit.

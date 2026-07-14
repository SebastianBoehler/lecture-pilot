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

Start from the checked-in template, keep the resulting file outside source control, and restrict its
permissions before adding real values:

```bash
cp .env.example .env
chmod 600 .env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Use the generated URL-safe value for `LECTUREPILOT_POSTGRES_PASSWORD`. Set
`LECTUREPILOT_MODEL`, include it in `LECTUREPILOT_ALLOWED_MODELS`, and add the matching provider key.
The preflight reports missing setting names but never prints their values:

```bash
source .venv/bin/activate
python -m lecturepilot.production_preflight --env-file .env
```

Production forces database session auth, schema verification, trusted Host and Origin lists, HSTS,
`Secure`/`HttpOnly`/`SameSite=Lax` session cookies, bounded material processing, quotas, and the
persisted `/app/storage` root. Production startup rejects insecure cookie overrides, missing or
non-HTTPS origins, wildcard hosts, and non-PostgreSQL databases. Provider and university credentials
stay server-side. Alma is the only account login path, and production web builds omit both
development demo-login buttons.

Plain-HTTP local development deliberately leaves the `Secure` cookie flag off because browsers would
otherwise reject the session. The production Compose path has no such override: Caddy obtains and
renews certificates, redirects HTTP to HTTPS, and adds HSTS before traffic reaches the internal web
or API services.

Validate without starting the live stack:

```bash
docker compose --env-file .env -f deploy/compose.yml config --quiet
docker compose --env-file .env -f deploy/compose.yml build
```

`docker compose up` runs the same preflight as a one-shot service before database migration and API
startup. Missing or unsafe configuration therefore stops the deployment instead of degrading to
development behavior.

The API image runs as UID 10001 with a read-only root, dropped capabilities, a temporary `/tmp`, and
CPU/memory/process limits. Gateway, web, and database use patched derived images recorded in
`deploy/`.

TeX compilation runs in the separate `latex-compiler` service. It receives one bounded source
archive, has no database or provider credentials, has no external network, forces Beamer handout
mode, disables shell escape, and returns only a bounded PDF. The API preserves uploaded matching
PDFs as authoritative and stores compiled PDFs and rendered pages only under the normalized source
directory.

## Storage and recovery

Postgres stores identity, roles, sessions, ownership, enrollments, audit, and quota state. The named
storage volume contains course and learner files. They form one recovery unit and must be backed up,
restored, encrypted, and versioned together. Follow `docs/security-operations.md`; a successful
restore rehearsal is a live-release gate.

## Upload and parser limits

`WorkspacePolicy` applies per-type byte limits. Uploads stream to quarantine, validate signature and
MIME, reject active SVG and unsafe paths, and promote atomically. PDF extraction and rendering run in
bounded worker processes with page, pixel, CPU, memory, file, and timeout limits. TeX compilation is
additionally isolated in the internal-only compiler container; a failure leaves the parsed text
canvas usable and adds a professor-facing warning.

## Current release blockers

Do not host publicly until all blockers in `security_best_practices_report.md` are closed. In
particular, student Alma/ILIAS identifier matching across representative accounts, disposable TLS
staging, backup restore, retention, deletion, privacy notice, and provider/subprocessor review remain
unverified or incomplete. The pinned `tue-api-wrapper==0.3.0` and Pillow 12.3 dependency set passes
the current Python audit.

# Self-hosting notes

LecturePilot is designed for one hardened shared service, not per-user containers or arbitrary host
filesystem access. A live pilot has been deployed from the checked-in Compose topology. The files
document the intended runtime, but neither the deployment nor this document closes the outstanding
security and privacy gates.

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
- `LECTUREPILOT_COMMIT_SHA` set to the exact deployed Git commit
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
Export the exact source revision before validating, building, or starting Compose:

```bash
export LECTUREPILOT_COMMIT_SHA="$(git rev-parse HEAD)"
```

Compose passes this value as an API-image build argument and as the expected runtime revision. The
build writes it into the image, and the API, preflight, and migration services all reference that
immutable revision-tagged image. `/api/health` reads only the baked value and returns unavailable if
it differs from the expected revision. Container preflight rejects the same mismatch before startup.
The API package version is read from the installed package metadata.

`/api/health` is the cheap process/build liveness check. `/api/ready` additionally verifies a live
Postgres query and the isolated compiler health response; Compose requires both the build-identity
check and runtime readiness before marking the API healthy. Neither endpoint returns connection
details.

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

Validate the Compose configuration without starting the live stack:

```bash
export LECTUREPILOT_COMMIT_SHA="$(git rev-parse HEAD)"
docker compose --env-file .env -f deploy/compose.yml config --quiet
```

Deploy a routine application update with:

```bash
scripts/deploy-production.sh
```

The deployment script checks Docker's filesystem for at least 1 GiB of free space before building,
then builds only the API and web images, one at a time. It does not rebuild the database, gateway, or
LaTeX compiler during an application-only release. Preflight and migration run against the existing
infrastructure before Compose recreates only the API and web services. If a build fails, incomplete
BuildKit cache and dangling images are removed automatically; named volumes are never pruned. Old
unused cache and images are retained for seven days after a successful release to keep one recent
rollback path and useful dependency layers without allowing Docker storage to grow indefinitely.

Compose runs the preflight as a one-shot service before database migration and API startup, with
image-identity verification enabled. Missing or unsafe configuration and stale API images therefore
stop the deployment instead of degrading to development behavior. Rebuild infrastructure services
explicitly only when their Dockerfile or runtime configuration changes and the host has sufficient
headroom.

The API image runs as UID 10001 with a read-only root, dropped capabilities, a temporary `/tmp`, and
CPU/memory/process limits. Gateway, web, and database use patched derived images recorded in
`deploy/`.

TeX compilation runs in the separate `latex-compiler` service. It receives one bounded source
archive, has no database or provider credentials, has no external network, forces Beamer handout
mode, and returns only a bounded PDF. The pinned Tectonic runtime uses a build-seeded bundle with
`--only-cached --untrusted`; it cannot download packages or execute shell commands. The API
preserves uploaded matching PDFs as authoritative and stores compiled PDFs and rendered pages only
under the normalized source directory.

## Storage and recovery

Postgres stores identity, roles, sessions, ownership, enrollments, audit, and quota state. The named
storage volume contains course and learner files. They form one recovery unit and must be backed up,
restored, encrypted, and versioned together. Follow `docs/security-operations.md`; a successful
restore rehearsal is a live-release gate.

The production database preloads `pg_stat_statements` and enables I/O timing. The migration creates
the normalized-statistics extension, but application logs never emit SQL text or bound parameters.
When upgrading an existing stack, recreate the `db` service with the new preload command before
running the migration service.
API and compiler metadata logs live in their own persistent, daily-rotated named volumes; see
`docs/observability.md` for retention and inspection commands.

## Upload and parser limits

`WorkspacePolicy` applies per-type byte limits. Uploads stream to quarantine, validate signature and
MIME, reject active SVG and unsafe paths, and promote atomically. PDF extraction and rendering run in
bounded worker processes with page, pixel, CPU, memory, file, and timeout limits. TeX compilation is
additionally isolated in the internal-only compiler container; a failure leaves the parsed text
canvas usable and adds a professor-facing warning.

## Current pilot blockers

The live pilot is not production-security approval. Do not expand access until all blockers in
`security_best_practices_report.md` are closed or explicitly accepted. In particular, student
Alma/ILIAS identifier matching across representative accounts, disposable TLS staging, backup
restore, retention, deletion, privacy notice, and provider/subprocessor review remain unverified or
incomplete. The pinned `tue-api-wrapper==0.3.0` and Pillow 12.3 dependency set passed the recorded
Python audit.

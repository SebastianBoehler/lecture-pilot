# LecturePilot pre-deployment security review

Date: 2026-07-11<br>
Reviewed baseline: `main` at `386a700`, plus the local release-polish worktree<br>
Verdict: **Do not deploy live yet**

## Executive summary

The original application-level high findings are remediated locally. LecturePilot now has
database-backed student and professor identity, approval, roles, course ownership, enrollments,
opaque revocable sessions, CSRF protection, self-only learner workspaces, aggregate-only professor
analytics, symlink-safe
agent/file capabilities, guarded uploads and parsers, durable quotas, and a same-origin hardened
container stack.

The published `tue-api-wrapper==0.3.0` requires Pillow 12.3, and the regenerated Python lock
passes `pip-audit`; the previous high dependency blocker is closed. Representative cross-account
Alma/ILIAS identifiers, live TLS/VM isolation, restore, and the legal retention/privacy policy remain
unverified. No VM access or deployment occurred.

No minimum analytics cohort is imposed. Course owners receive only aggregate values that actually
exist, or an explicit no-data result. Platform course search, join requests, tutor invitations, and
co-instructor delegation are not implemented.

## Confirmed authorization model

| Capability                                                      | Holder                  |
| --------------------------------------------------------------- | ----------------------- |
| Approve/reject professor requests and disable accounts          | Platform administrator  |
| Create a course                                                 | Approved professor      |
| Manage source, schedule, publication, media, analytics, archive | Exact course owner      |
| Learn from published and unlocked course material               | Active enrolled student |
| Canvas, tutor, memory, generated files, readiness, reset        | That learner only       |

Platform administrators do not gain course-content access. Professor status grants course creation,
not access to all courses. Details and the route inventory are in `docs/tenancy-security.md`.

## University course matching

LecturePilot does not attempt to enumerate Alma or ILIAS. A professor creates a platform course with
title and term. Student login returns only that student's memberships.

- Alma `unitId` and ILIAS course/ref IDs are required as stable upstream identifiers.
- An existing `(tenant, source, external ID, term)` link is reused.
- A new link requires exactly one normalized exact title plus exact term match.
- Zero or multiple platform matches grant no enrollment.
- After binding, the stable upstream ID remains authoritative across title changes.

Evidence: `external_course_sync.py:21-193`, `tuebingen_adapter.py:23-140`, and
`test_database_security.py`.

## Finding status

### H-1 — Identity, sessions, and professor roles: remediated locally

SQLAlchemy/Postgres/Alembic models now store users, external identities, tenant memberships,
professor requests, sessions, courses, external refs, enrollments, audit events, and quotas.
Sessions are random opaque values; only hashes are stored. Approval and disablement revoke existing
sessions. Production fails when the database is absent or behind the current migration.

Students and professor candidates authenticate through the same university adapter. An active Alma
`student` role remains a student; any other active role creates a pending professor request and
grants no role until a platform administrator approves it. The raw Alma role remains visible for
review, and approval revokes the pending session so the professor must sign in again. Production
builds render neither demo login.

Evidence: `database.py:21-83`, `session_store.py:34-103`, `identity_repository.py:23-184`,
`professor_identity_repository.py`, `professor_auth_routes.py`, `approval_routes.py`, and migrations
`20260710_0001` through `0003`.

### H-2 — Cross-course and learner access: remediated locally

Course authority comes from `courses.owner_user_id`. Every learner route derives the learner from
the session; learner IDs were removed from agent, quiz, canvas, and reset inputs. Workspace assets
are self-only. Professor analytics expose aggregate records without learner keys, text, chats,
canvases, or readiness attempts.

Evidence: `api_auth.py:85-121`, `course_routes.py:49-265`, `analytics_routes.py`,
`course_canvas_routes.py`, and `test_database_security.py`.

### H-3 — CSRF: remediated locally

Cookie-authenticated mutations require the session-bound token, an allowed exact Origin, and Fetch
Metadata validation. The frontend adds the header centrally. Missing token, wrong Origin, and valid
same-origin cases have regression tests.

Evidence: `csrf.py:24-59`, `session_store.py`, `apps/web/src/authz.ts`, and
`test_database_security.py`.

### H-4 — Symlink/path escape: remediated locally

`WorkspaceFS` performs logical-root resolution, Unicode normalization, hidden/traversal rejection,
descriptor-relative no-follow opens, and hard-link rejection. Agent tools, source scanning, uploads,
and asset serving use the same boundary. The learner agent retains recursive navigation and writes
within only its declared writable roots.

Evidence: `workspace_fs.py:17-179`, `workspace_capability.py`, `safe_course_files.py`,
`test_workspace_fs_security.py`, and `test_agent_tool_roots_security.py`.

### H-5 — Multipart denial of service: remediated locally

`python-multipart` is pinned to 0.0.32. Request body limits remain enabled, and accepted uploads are
streamed to quarantine rather than read wholly into memory.

Evidence: `apps/api/pyproject.toml`, `requirements.lock`, `secure_upload.py:22-134`.

### H-6 — Model authority and cost abuse: remediated locally

The browser cannot choose a model. The server validates an allowlist. Postgres atomically enforces
daily turns, reserved tokens, image counts, and concurrent turns across workers and restarts.

Evidence: `providers.py`, `usage_quota.py:38-181`, `agent_turn_orchestration.py`, and
`test_usage_quota.py`.

### H-7 — Deployment path and persistence: implemented, not live-verified

The web build uses same-origin `/api`; Caddy provides HTTPS and redirects; only 80/443 are published.
API, web, and database stay internal. The API runs as UID 10001 with a read-only root, dropped
capabilities, resource limits, and a persisted `/app/storage` volume. Migrations complete before API
startup. Gateway, web, and database images were rebuilt on patched runtimes.

Evidence: `deploy/compose.yml`, `deploy/Caddyfile`, `deploy/Caddy.Dockerfile`,
`deploy/Postgres.Dockerfile`, and both application Dockerfiles.

### M-1 — Unsafe uploads and parsing: remediated locally

Uploads use per-type byte limits, MIME/signature checks, quarantine, atomic no-overwrite promotion,
and active SVG rejection. PDF preview, slide rendering, and extraction run in a bounded process pool
with page/pixel/time/CPU/memory/file limits. Production-style worker tests passed on macOS and Linux.

Evidence: `secure_upload.py`, `bounded_processing.py:16-69`, `pdf_preview.py`,
`pdf_slide_assets.py`, `pdf_extract.py`, and `test_secure_upload.py`.

### M-2 — Readiness answers before attempt: remediated locally

The public check DTO excludes answer indices and rubrics. Submission reconstructs the canonical
server-side check before scoring. Browser and API tests confirm the answer is absent before submit.

Evidence: `exam_readiness.py:46-76`, `exam_readiness_routes.py`, and readiness tests.

### M-3 — Hostile source instructions: reduced

Prompts label source, canvas, tool output, and memory as untrusted. Durable memory and paid image
actions require an explicit current learner request. Typed tools and capabilities still enforce the
real boundary if a model follows hostile content.

Evidence: `model_client.py`, `agent_side_effect_tools.py`, and agent tool tests.

### M-4/L-1 — Privacy, audit, and response leakage: partially remediated

Audit records cover login, account changes, course lifecycle, upstream binding, uploads,
publication, aggregate analytics, and reset. Public DTOs omit host storage paths and unnecessary
publisher identity. Course deletion is a soft archive. Automated physical deletion, learner data
export/deletion, approved retention periods, legal notice, and subprocessor inventory remain open.

Evidence: `audit.py`, route modules, `docs/security-operations.md`.

## Remaining live-release blockers

1. **Real university fixtures:** confirm stable Alma/ILIAS IDs across representative student accounts
   and both supported enrollment paths. University data must never grant the professor role.
2. **Disposable staging:** verify public TLS, redirects, trusted Host, Origin/CSRF rejection, secure
   cookies, public ports, non-root runtime, approval, matching, isolation, quotas, and backup/restore.
3. **Privacy operations:** approve controller/contact, legal basis, provider/subprocessor inventory,
   retention periods, learner export/deletion, backup expiry, and incident-notification ownership.

## Verification evidence

Passed locally:

- API: 285 tests.
- Web: 86 tests; TypeScript/Vite production build. Heavy lesson, professor, and article views are
  lazy-loaded; the eager entry bundle is 285.60 kB minified / 87.44 kB gzip.
- Quality: ESLint, Ruff, and Knip; existing React hook warnings remain non-failing.
- PostgreSQL: Alembic drift check and downgrade/upgrade; production schema verification.
- Security: CSRF/object authorization, Alma+ILIAS matching, symlink/hard-link/Unicode confinement,
  upload validation, quotas, pre-attempt answer withholding, and bounded Linux worker.
- Dependencies: npm production audit and a fresh Python lock audit report zero known
  vulnerabilities. `tue-api-wrapper==0.3.0` resolves to Pillow 12.3 and `defusedxml`.
- Secrets: Trivy repository secret scan found no secret.
- Containers: gateway, web, API, and database images build; API is UID 10001; production JS contains
  no localhost API URL; Caddy config validates. Current images have zero fixed high/critical
  findings.
- Browser: the unified Alma professor fixture reaches a pending profile without professor
  privileges; approval revokes the pending session and a fresh login unlocks owned-course creation.
  Earlier course creation, guarded
  upload/index, schedule inference, media search, generated draft, publication, separate-student
  dashboard/canvas, quiz, and tutor request passed with zero final-page console errors. The run
  caught and fixed discovered-lecture authorization, oversized provider metadata, and draft-preview
  course-scope regressions.

Not performed: a login with real professor Alma credentials, real cross-account university
identifier comparison, disposable hosted staging, live VM/SSH, TLS/browser verification, restore
rehearsal, provider data-retention review, or legal/privacy approval.

## Deployment decision

Do not deploy to the live VM. Complete the real university identifier check, approve
privacy/retention operations, and pass disposable staging. The current work is a locally verified
remediation implementation, not a production authorization.

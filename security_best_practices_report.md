# LecturePilot pilot security status

Review refreshed: 2026-07-20<br>
Implementation baseline: release `0.2.1`, commit
`a854cfa5c5a9c98fd33066bc756c73b3c9ad4e09`<br>
Decision: **the live pilot is hardened, but broader production approval remains
blocked by the operational and privacy gates below**

This is the current status document. The older implementation sequence is
preserved as a historical record in
[`docs/security-remediation-implementation-plan.md`](docs/security-remediation-implementation-plan.md).

## Scope and evidence

The refresh checked the FastAPI authorization/session/upload/workspace code and
tests, React API/auth boundary, Alembic/Postgres models, production Compose and
Dockerfiles, Caddy/nginx policy, Tectonic service, dependency locks, and current
operator documentation.

A point-in-time live check on 2026-07-20 confirmed:

- public `/api/health` returned `0.2.1` and the exact baseline SHA;
- API, Postgres, and Tectonic containers reported healthy;
- only Caddy published host ports 80/443;
- the host filesystem was 12% used and `/var` was 32% used; and
- HTTPS returned CSP, one-year HSTS, `no-referrer`, `nosniff`, frame denial,
  and a restrictive Permissions Policy.

The live check did not use real professor/student credentials, perform an
authorization attack suite against production, inspect provider retention, or
restore a backup.

## Confirmed authorization model

| Capability                                                                 | Holder                                                                    |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Authenticate                                                               | University identity verified by the server-side Alma adapter              |
| Create a course                                                            | Account whose active Alma role is not `student`                           |
| Manage source, schedule, drafts, publication, media, and course aggregates | Exact course owner                                                        |
| Learn from a course                                                        | Current enrollment or the course's explicit access policy                 |
| Open an unpublished/future lecture                                         | Nobody through learner routes                                             |
| Canvas, tutor, memory, assets, readiness, profile, and reset               | That learner only                                                         |
| Disable an account                                                         | Platform administrator; this does not grant course/learner content access |

Browser role, tenant, course, learner, and model values are never authority in
production. Tutor/co-instructor delegation and platform course join requests
are not implemented.

## Implemented controls

### Identity, sessions, and CSRF

- The submitted university password is used only for the server-side login
  call and is not persisted or returned.
- The server-reported active Alma `student` role maps to learner; any other
  active Alma role maps directly to professor. Available roles are stored for
  audit. There is no separate local professor-password or approval flow.
- Sessions are random opaque tokens; the database stores SHA-256 token and CSRF
  hashes, expiry, revocation, user, and tenant. Logout and account disablement
  revoke authority.
- Production cookies are `Secure`, `HttpOnly`, and `SameSite=Lax`.
  Cookie-authenticated mutations require the session CSRF token, an exact
  HTTPS Origin, and same-site Fetch Metadata. Bearer-authenticated server calls
  do not use the cookie-CSRF path.

### Course and learner isolation

- Course administration requires professor role, same tenant, and exact
  `courses.owner_user_id`; professor status is not tenant-wide course access.
- Student routes reconstruct the learner from the session and verify course
  visibility/enrollment, publication, and lecture date.
- Workspace assets bind the URL's pseudonymous key back to the current learner.
- Professors receive aggregate usage/performance only. Ordinary professor and
  platform-admin routes cannot read learner canvas, chat, memory, generated
  files, readiness attempts, or reset state.
- Professor learner preview uses a separate owner-derived workspace and is
  excluded from learner/cohort analytics.

### University enrollment matching

Login deactivates stale Alma/ILIAS-derived enrollments before background sync.
For each current upstream observation, LecturePilot reuses a previously bound
`(tenant, source, external_course_id, term)` reference. A new reference is
created only when normalized exact title plus exact term matches exactly one
active `tuebingen_enrolled` platform course. Zero or multiple matches grant no
enrollment. ILIAS supplies stable reference IDs; the lightweight Alma timetable
path remains exact-title-and-term dependent.

### Files, parsers, and TeX

- Capability roots use normalized logical paths, descriptor-relative no-follow
  access, and hard-link rejection. Source, learner, preview, and builder write
  capabilities are separate.
- Uploads stream to quarantine with request/per-type limits, SHA-256,
  MIME/signature checks, active-SVG rejection, and atomic no-overwrite
  promotion.
- PDF extraction/rendering uses bounded processes with page, pixel, CPU,
  memory, file, and timeout limits. Notebook/Python ingestion never executes
  code.
- Uploaded TeX never runs in the API. The internal Tectonic service is
  read-only, resource-limited, no-secret, external-network isolated, and uses a
  build-seeded bundle with `--only-cached --untrusted`. Shell escape and runtime
  package downloads remain disabled.

### Providers, cost, logging, and deployment

- Provider keys remain server-side. The server validates the configured model
  against an allowlist and checks capabilities before a request.
- Postgres atomically enforces daily turn/token/image and concurrent-turn
  quotas across workers and restarts. Request-body and route rate limits add a
  separate front-line bound.
- Audit events cover identity sync, external-course binding, account disable,
  course lifecycle, uploads/updates, publication, aggregate analytics access,
  learner profile changes, and learner reset.
- Production JSONL observability is metadata-only and excludes prompts,
  responses, source content, filenames, raw learner content, credentials,
  request URLs, query strings, and exception messages.
- Caddy is the only public service. API and compiler run with read-only roots,
  dropped capabilities, no-new-privileges, temporary filesystems, and CPU,
  memory, and process limits. Postgres and application storage use persistent
  volumes.

## Residual risks and release gates

### High-priority operational gates

1. **Representative university fixtures:** verify current Alma and ILIAS
   identifiers and matching across multiple real student accounts, terms,
   duplicate titles, and role types. Confirm that no student observation can
   produce professor authority.
2. **Disposable staging authorization suite:** exercise TLS redirects, Host,
   Origin/CSRF, cookie flags, cross-owner/course/learner denials, quota
   exhaustion, upload rejection, compiler isolation, and public-port inventory
   against a non-production deployment.
3. **Matched recovery rehearsal:** back up and restore Postgres plus the exact
   storage-volume snapshot, migrate it, and prove owner/learner isolation and
   asset/audit integrity before relying on recovery.
4. **Privacy operations:** approve controller/contact, legal basis, notice,
   provider/subprocessor inventory, retention and backup expiry, learner
   export/deletion, physical course deletion, and incident-notification owners.

### Known implementation boundaries

- Content signature and MIME validation are not malware scanning. Introduce a
  quarantine scanner before accepting formats/risk levels that require it.
- Protected files currently stay behind authenticated API routes on a
  persistent volume. S3-compatible storage and short-lived signed delivery are
  future work, not deployed controls.
- Prompt-injection instructions reduce model misuse but are not a security
  boundary; typed capabilities, server authorization, quotas, and source
  immutability are the boundary.
- Tectonic intentionally does not support every TeX workflow. Unsupported
  shell escape, Biber, raw-SVG conversion, host fonts, or unseeded packages
  require an authoritative uploaded PDF or a reviewed image rebuild, never a
  weaker runtime sandbox.
- Course deletion is a soft archive. Automated physical deletion and learner
  data export/deletion are not implemented.

## Verification expectations

Repository changes must pass the component checks used by CI:

```bash
npm run verify:api
npm run verify:web
```

Security-sensitive changes additionally need the narrow authorization,
session/CSRF, workspace, upload, quota, bounded-processing, and compiler tests
that own the changed boundary. Dependency/container scans and the real-account,
staging, privacy, and recovery gates are release evidence; passing unit tests
alone does not close them.

## Operating decision

Keep the current deployment constrained as a pilot. Do not expand access or
describe it as production-approved until the four high-priority gates are
completed or explicitly accepted by the responsible operator/controller with
scope, owner, and review date recorded.

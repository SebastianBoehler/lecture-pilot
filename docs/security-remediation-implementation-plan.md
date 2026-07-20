# Historical security remediation record

> Historical record from 2026-07-10 through 2026-07-14. The implementation
> plan landed, and several product decisions changed afterward. Do not use this
> file as current security or operating guidance. See
> [`../security_best_practices_report.md`](../security_best_practices_report.md),
> [`tenancy-security.md`](tenancy-security.md), and
> [`security-operations.md`](security-operations.md).

Original baseline: `01608fe`<br>
Implementation baseline at the end of this effort: `386a700`<br>
Current reviewed product baseline: release `0.2.1` at `a854cfa`

## Why this work existed

The early prototype trusted local/demo identities, filesystem state, and broad
course context too heavily for a university pilot. The remediation established
database authority, object-level authorization, bounded untrusted-file
handling, provider-cost controls, and a hardened deployment path before the
course-builder and learner features expanded.

## Completed implementation groups

### Database identity and sessions

- Added SQLAlchemy/Postgres models and Alembic migrations for users, external
  identities, tenant memberships, sessions, courses, upstream references,
  enrollments, audit events, and quotas.
- Replaced browser-contained authority with random opaque session tokens whose
  hashes are stored in Postgres.
- Added expiry, revocation, account disablement, `GET /me`, and production
  startup/schema checks.
- Added exact Origin, Fetch Metadata, and session-bound CSRF checks for
  cookie-authenticated mutations.

### Roles, ownership, and enrollment

- Unified university login and persisted server-reported Alma roles.
- Made the creator the exact course owner; professor role alone grants no
  access to another professor's course.
- Removed browser learner IDs from learner operations and made canvas, assets,
  tutor, readiness, profile, memory, analytics events, and reset self-only.
- Added conservative upstream matching: reuse stable source references, or
  create one only for a unique normalized-title plus exact-term match.
- Restricted professor analytics to owned-course aggregates without learner
  identifiers or content.

### Files, parsers, and model authority

- Added capability-scoped workspace roots, normalized path checks,
  descriptor-relative no-follow access, and hard-link rejection.
- Added streaming quarantine, per-type limits, signature/MIME validation,
  active-SVG rejection, and atomic promotion for professor uploads.
- Bounded PDF extraction/rendering and made notebook/Python ingestion inert.
- Moved TeX compilation into a separate no-secret, internal-only service; the
  later Tectonic migration retained that boundary.
- Added server model allowlists plus durable daily/concurrent turn, token, and
  image quotas.

### Deployment, audit, and privacy reduction

- Added same-origin Caddy routing, HTTPS/HSTS, hardened API/web/database images,
  internal-only service networks, read-only roots, dropped capabilities,
  resource limits, and persistent Postgres/application volumes.
- Added audit events for the account, enrollment binding, course, upload,
  publication, aggregate-view, profile, and reset actions that need durable
  provenance.
- Removed answer/rubric leakage before readiness attempts and host paths from
  public DTOs.
- Added metadata-only observability that excludes prompts, responses, learner
  text, source content, filenames, credentials, raw URLs, and exception text.

## Superseded decision

The original plan proposed a platform-admin approval queue for every
non-student Alma identity. That workflow was removed. The current rule trusts
the active role returned by Alma: `student` maps to learner and any other active
role maps directly to professor. Platform administration can disable accounts
but does not approve professor requests or gain course/learner content access.

This is why old references to “pending professor”, approval/rejection, or
session revocation after professor approval must not be copied into current
documentation or tests.

## Gates deliberately left open

The implementation work did not close these operational/product obligations:

1. representative real-account Alma/ILIAS identifier and role fixtures;
2. a disposable hosted authorization/TLS/isolation test pass;
3. a matched Postgres plus storage-volume restore rehearsal;
4. approved retention, backup expiry, learner export/deletion, privacy notice,
   legal basis, and provider/subprocessor inventory;
5. malware scanning for uploaded course material; and
6. S3-compatible storage and short-lived signed delivery if protected assets
   move off the authenticated API/volume path.

These are tracked as current release gates in the security status report. The
fact that a live pilot exists does not implicitly accept or close them.

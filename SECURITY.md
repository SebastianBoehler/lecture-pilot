# Security

Please report suspected vulnerabilities privately to the repository owner. Do
not include credentials, university data, course material, or learner data in a
public GitHub issue.

## Current Security Posture

- University login is handled server-side. Submitted passwords are not stored;
  the browser receives an `HttpOnly`, `Secure`, `SameSite=Lax` opaque session
  cookie, and the database stores only session and CSRF hashes.
- Tenant role, exact course ownership, current enrollment, learner identity,
  publication, and lecture unlock checks are backend-enforced. The browser
  cannot grant itself a role, tenant, course, learner, or model.
- Cookie-authenticated mutations require a session-bound CSRF token, an exact
  allowed Origin, and same-site Fetch Metadata.
- Course and learner files use capability-scoped, symlink-safe roots. Uploads
  are streamed through quarantine, checked against per-type limits and content
  signatures, and atomically promoted.
- Model/image quotas, audit events, metadata-only production logs, and provider
  model allowlists are durable backend controls.
- Uploaded TeX is compiled only in the internal, no-secret Tectonic service
  with no external network, cached packages, `--untrusted`, and resource limits.
- Production uses same-origin HTTPS, hardened containers, Postgres, and a
  persisted application-storage volume. Only the gateway publishes ports.

## Open Operational And Product Gaps

- Malware scanning is not implemented; MIME/signature checks are not a malware
  scanner.
- The current deployment serves protected files through authenticated API
  routes on a persistent volume. An object-storage adapter and short-lived
  signed URLs are required before moving protected files to S3-compatible
  storage.
- Automated learner export/deletion, physical course deletion, approved
  retention periods, backup expiry, and the final privacy/subprocessor process
  remain open.
- Representative real-account Alma/ILIAS matching, disposable staging security
  checks, and a matched database/storage restore rehearsal remain release gates.

See [`security_best_practices_report.md`](security_best_practices_report.md) for
the evidence and risk decision, and
[`docs/security-operations.md`](docs/security-operations.md) for operator
procedures.

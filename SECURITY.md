# Security

Please report security issues privately to the repository owner.

## Current Security Posture

- Provider keys are server-side only.
- The workspace API rejects hidden paths, traversal, oversized writes, and unsafe
  generated file types.
- Lecture unlock policy is enforced outside the prompt.
- Tenant roles, profile memberships, and first-pass professor upload policy are
  modeled and tested in the API.
- Tenant storage/cache prefixes are hashed so storage keys do not expose tenant
  names directly.

## Not Yet Implemented

- Production authentication.
- Persistent encrypted university sessions.
- Object storage signing.
- Malware scanning and MIME sniffing for professor material uploads.
- Persistent tenant/profile/course enrollment tables.
- Per-user quotas beyond local policy checks.
- Full audit logging.

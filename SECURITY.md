# Security

Please report security issues privately to the repository owner.

## Current Security Posture

- Provider keys are server-side only.
- The workspace API rejects hidden paths, traversal, oversized writes, and unsafe
  generated file types.
- Lecture unlock policy is enforced outside the prompt.

## Not Yet Implemented

- Production authentication.
- Persistent encrypted university sessions.
- Object storage signing.
- Per-user quotas beyond local policy checks.
- Full audit logging.


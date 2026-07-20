# Security operations runbook

This runbook describes the minimum procedure for staging and the deployed live pilot. Its existence,
and the fact that the pilot is running, are not production security approval.

## Backup

Back up Postgres and the `lecturepilot-storage` volume as one versioned set. Encrypt the result,
restrict operator access, and record the migration revision and image digests. Never copy backups
into the repository.

```bash
docker compose -f deploy/compose.yml exec -T db \
  pg_dump -U lecturepilot -Fc lecturepilot > \
  "${LECTUREPILOT_BACKUP_DIR:?Set an encrypted external backup directory}/lecturepilot-db.dump"
docker run --rm -v deploy_lecturepilot-storage:/source:ro \
  -v "${LECTUREPILOT_BACKUP_DIR:?Set an encrypted external backup directory}:/backup" alpine:3.23 \
  tar -C /source -czf /backup/lecturepilot-storage.tgz .
```

The backup directory must be outside the repository and protected like production learner data.

## Restore rehearsal

Restore only into an isolated disposable environment first. Stop API writes, restore Postgres and
the storage volume from the same backup set, run `alembic upgrade head`, and verify:

- API starts with schema verification enabled;
- an owner can open course administration but an unrelated professor receives `403`;
- a learner can open only their own enrolled course and workspace;
- a sample stored asset and audit event survived the restore.

Do not overwrite a live volume until the rehearsal and integrity checks pass.

## Account and session response

- Disabling an account uses `POST /platform/users/{user_id}/disable` and revokes its sessions.
- The active server-reported Alma role determines student/professor access on each synchronized
  identity snapshot. A role change takes effect through a new university login; disabling the
  LecturePilot account remains the immediate local revocation path.
- A suspected session theft requires account disablement or direct session revocation, review of
  `audit_events`, and rotation of any exposed session/provider/database secret.
- Provider keys and the database password live only in the deployment secret source, never Compose,
  browser storage, logs, or repository files.

## Audit review

Review failed authorization metadata and database audit events for login, account disablement,
course creation/archive, upstream-reference binding, upload, publication, aggregate analytics
access, and learner reset. Alert on repeated cross-course denials, unusual paid usage, quota
exhaustion, or repeated malformed uploads.

## Retention and deletion status

Course deletion is a soft archive. Automated physical deletion, learner export/deletion, backup
expiry, legal retention periods, privacy notice details, and the final provider/subprocessor
inventory are not implemented or approved. These are live-release blockers; operators must not
invent retention periods or manually delete partial records without an approved policy.

## Incident sequence

1. Contain: disable affected accounts, revoke sessions, stop the exposed service if necessary.
2. Preserve: retain audit records and immutable logs without copying learner content broadly.
3. Rotate: replace affected session, database, university-wrapper, model, and image-provider secrets.
4. Recover: restore the matched database/storage set in isolation and run authorization smoke tests.
5. Review: document scope, affected data, decisions, and required notifications with the responsible
   controller before reopening access.

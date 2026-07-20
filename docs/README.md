# Documentation map

This index separates current operating documentation from historical design
records. Current documents were checked against the implementation and deployed
Compose topology on 2026-07-20.

## Current product and engineering documentation

| Document                                                                       | Scope                                                             |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| [`../README.md`](../README.md)                                                 | Product overview, setup, releases, and verification               |
| [`architecture.md`](architecture.md)                                           | Deployed services, trust boundaries, storage, and agent runtime   |
| [`course-ingestion-pipeline.md`](course-ingestion-pipeline.md)                 | Course creation, updates, generation, repair, and publication     |
| [`workspaces.md`](workspaces.md)                                               | Course, learner, preview, and legacy storage paths                |
| [`agent-tool-contracts.md`](agent-tool-contracts.md)                           | Tool profiles, logical roots, and side effects                    |
| [`latex-compilation.md`](latex-compilation.md)                                 | Isolated Tectonic setup and compatibility boundary                |
| [`tectonic-parity.md`](tectonic-parity.md)                                     | Corpus and synthetic migration evidence                           |
| [`media-discovery.md`](media-discovery.md)                                     | Professor-reviewed YouTube integration                            |
| [`observability.md`](observability.md)                                         | Metadata logging and optional MLflow tracing                      |
| [`self-hosting.md`](self-hosting.md)                                           | Production Compose, deployment, and recovery requirements         |
| [`tenancy-security.md`](tenancy-security.md)                                   | Current principals, authorization matrix, and enrollment matching |
| [`security-operations.md`](security-operations.md)                             | Backup, incident, retention, and deletion runbook                 |
| [`../SECURITY.md`](../SECURITY.md)                                             | Security reporting and current control summary                    |
| [`../security_best_practices_report.md`](../security_best_practices_report.md) | Evidence-backed pilot security status and open gates              |

## Developer and module notes

- [`../AGENTS.md`](../AGENTS.md) — repository rules, setup, ownership, and
  verification for coding agents.
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — contributor checks.
- [`../apps/api/README.md`](../apps/api/README.md) — current API responsibilities.
- [`../integrations/tuebingen/README.md`](../integrations/tuebingen/README.md) —
  current university-integration boundary.
- `packages/*/README.md` and `services/agent/README.md` — explicitly reserved
  boundaries; they are not deployed packages/services.

## Historical records

The following files preserve the reasoning or implementation sequence from a
specific date. Their headers link back to the current source of truth; they are
not runtime, setup, or security guidance.

- [`glm-5.1-ui-design.md`](glm-5.1-ui-design.md)
- [`../design-qa.md`](../design-qa.md)
- [`security-remediation-implementation-plan.md`](security-remediation-implementation-plan.md)
- [`superpowers/specs/2026-06-10-workspace-storage-redesign.md`](superpowers/specs/2026-06-10-workspace-storage-redesign.md)
- [`superpowers/plans/2026-06-18-interleaved-slides.md`](superpowers/plans/2026-06-18-interleaved-slides.md)
- [`superpowers/plans/2026-07-01-adaptive-exam-readiness.md`](superpowers/plans/2026-07-01-adaptive-exam-readiness.md)

When behavior changes, update the current document that owns the contract in
the same pull request. Do not revise historical records to describe a newer
implementation; add a status note or link instead.

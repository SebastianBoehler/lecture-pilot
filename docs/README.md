# Documentation map

This index separates current operating documentation from historical design
records. Current documents were checked against the implementation on
2026-08-09. The last live deployed-Compose evidence remains the 2026-07-20
snapshot identified in the security status report.

## Current product and engineering documentation

| Document                                                                 | Scope                                                             |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| [`../README.md`](../README.md)                                           | Product overview, setup, releases, and verification               |
| [`architecture.md`](architecture.md)                                     | Deployed services, trust boundaries, storage, and agent runtime   |
| [`course-ingestion-pipeline.md`](course-ingestion-pipeline.md)           | Course creation, updates, generation, repair, and publication     |
| [`course-updates.md`](course-updates.md)                                 | Lecture-local source revisions, update apply, lecture states      |
| [`professor-enablement.md`](professor-enablement.md)                     | Live introduction, tutorial recordings, and maintenance ownership |
| [`evaluation-contract.md`](evaluation-contract.md)                       | Draft review and future learning-evaluation boundaries            |
| [`workspaces.md`](workspaces.md)                                         | Course, learner, preview, and legacy storage paths                |
| [`agent-tool-contracts.md`](agent-tool-contracts.md)                     | Tool profiles, logical roots, and side effects                    |
| [`latex-compilation.md`](latex-compilation.md)                           | Isolated Tectonic setup and compatibility boundary                |
| [`tectonic-parity.md`](tectonic-parity.md)                               | Corpus and synthetic migration evidence                           |
| [`media-discovery.md`](media-discovery.md)                               | Professor-reviewed YouTube integration                            |
| [`observability.md`](observability.md)                                   | Metadata logging and optional MLflow tracing                      |
| [`self-hosting.md`](self-hosting.md)                                     | Production Compose, deployment, and recovery requirements         |
| [`tenancy-security.md`](tenancy-security.md)                             | Current principals, authorization matrix, and enrollment matching |
| [`security-operations.md`](security-operations.md)                       | Backup, incident, retention, and deletion runbook                 |
| [`../SECURITY.md`](../SECURITY.md)                                       | Security reporting and current control summary                    |
| [`security-best-practices-report.md`](security-best-practices-report.md) | Evidence-backed pilot security status and open gates              |

## Developer and module notes

- [`../AGENTS.md`](../AGENTS.md) — repository rules, setup, ownership, and
  verification for coding agents.
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — contributor checks.
- [`../apps/api/README.md`](../apps/api/README.md) — current API responsibilities.
- [`../integrations/tuebingen/README.md`](../integrations/tuebingen/README.md) —
  current university-integration boundary.

## Historical records

Dated design plans, demo logs and superseded implementation records were archived
out of the repository on 2026-10-11 to keep the documentation current. Git history
retains them. When behavior changes, update the current document that owns the
contract in the same pull request.

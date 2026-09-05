# Low-cost hosting: verified prices and capacity model

Checked 2026-09-04 against primary vendor pages and repository `8e656e2` plus
the local readiness fixes. This is a source-backed planning note, **not a VPS
benchmark or a measured user-capacity claim**. No server was bought or deployed.

## What does “a $5 VPS” currently buy?

| Provider / plan               | Monthly base price                     | CPU / memory / disk                  | Included transfer |
| ----------------------------- | -------------------------------------- | ------------------------------------ | ----------------- |
| Hetzner CX23, Germany/Finland | €5.49 or $6.49, excluding VAT and IPv4 | 2 shared vCPU / 4 GB / 40 GB NVMe    | 20 TB             |
| Hetzner CX33, Germany/Finland | €8.49 or $9.99, excluding VAT and IPv4 | 4 shared vCPU / 8 GB / 80 GB NVMe    | 20 TB             |
| DigitalOcean Basic Regular    | $4                                     | 1 shared vCPU / 512 MiB / 10 GiB SSD | 500 GiB           |
| DigitalOcean Basic Regular    | $6                                     | 1 shared vCPU / 1 GiB / 25 GiB SSD   | 1,000 GiB         |

Hetzner prices changed for new orders/rescales on June 15, 2026; the older
€3.99/$4.99 CX23 headline is not the current new-order price. Specifications
come from the product page, prices from the dated official adjustment notice.
Its public product page rendered availability as unavailable during inspection;
actual regional stock must be checked before ordering.
[Price adjustment](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/),
[CX specifications](https://www.hetzner.com/cloud/cost-optimized/).

Hetzner Primary IPv4 adds €0.50/$0.60 monthly, excluding VAT; IPv6 is free.
Thus CX23 plus IPv4 is €5.99/$7.09 before tax, backup, domain, and inference.
CX33 plus IPv4 is €8.99/$10.59 on the same basis. These are arithmetic totals,
not checkout quotes. [Official IP prices](https://docs.hetzner.com/general/infrastructure-and-availability/ipv4-pricing/).

DigitalOcean's current regular table has $4 and $6 tiers, not a $5 tier.
Backups are additional: its listed weekly percentage-based option adds 20%.
Treat all VM prices as infrastructure only, with applicable taxes and other
services separate. [Official Droplet pricing](https://www.digitalocean.com/pricing/droplets).

## What the current application actually runs

The [production Compose file](../../deploy/compose.yml) has a shared API and
shared course files, not a container or local model per learner:

```txt
HTTPS gateway -> static web + FastAPI -> external model provider
                         |-> Postgres: identity, sessions, ownership, quotas
                         |-> shared volume: course sources + learner overlays
                         |-> isolated TeX and document conversion services
```

The full deployed topology is more than a small Python process:

| Service                       | Checked-in ceiling                             | Capacity implication                                                          |
| ----------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------- |
| API                           | 2 CPU, 2 GiB RAM, 256 MiB temporary filesystem | Model orchestration, authenticated reads/writes and bounded source processing |
| TeX compiler                  | 1 CPU, 1 GiB RAM, 768 MiB temporary filesystem | One compile slot; overload returns a busy error                               |
| Document converter            | 2 CPU, 3 GiB RAM, 1 GiB temporary filesystem   | Office/document conversion; HTTP concurrency limited to 4                     |
| Postgres, gateway, static web | No explicit RAM ceiling in this Compose        | Additional RAM, disk, network and CPU usage                                   |

Temporary filesystem use consumes memory within the relevant container's limit;
do not add it a second time. Limits are ceilings, not reservations or measured
resident usage. The three capped services can together reach **6 GiB** before
Postgres, gateway, web, host OS and operational headroom. A 4 GB VM may run light
traffic but does not cover this declared simultaneous peak envelope. An 8 GB
class VM is a more credible full-stack test target, **not yet a fit guarantee**.
The API currently requires both helper services healthy at startup; simply
omitting them is not the existing production topology.

The [API image](../../apps/api/Dockerfile) sets HTTP concurrency 100, backlog
512 and keep-alive 5 seconds; it does not explicitly request multiple workers.
Uvicorn's concurrency limit counts connections/tasks and rejects overload with
503; it is not a guarantee of 100 students or 100 completed requests/second.
The backlog is not an application job queue.
[Uvicorn resource-limit semantics](https://uvicorn.dev/server-behavior/).

Relevant implementation details:

- [Application wiring](../../apps/api/src/lecturepilot/app.py) gives the tutor
  its model-usage recorder. [Model slots](../../apps/api/src/lecturepilot/model_rate_limits.py)
  permit at most **3 simultaneous calls per event loop and model** on this path;
  provider rate limits can reduce this to 1. This is not a cluster-wide quota.
- [Tool loop](../../apps/api/src/lecturepilot/agent_tool_loop.py) allows multiple
  sequential model calls per learner turn; do not assume one turn = one call.
  [Request accounting](../../apps/api/src/lecturepilot/model_usage.py) measures
  request attempts and retries, including wait versus provider timing.
- [Usage quota](../../apps/api/src/lecturepilot/usage_quota.py) defaults to one
  active turn per tenant/user/course/day scope. Its daily limits are protection
  rules, not throughput measurements or actual token expenditure.
- [Database](../../apps/api/src/lecturepilot/database.py) uses synchronous
  SQLAlchemy sessions and library-default pooling; production session/quota
  paths therefore need measurement, not just development-header canvas reads.
- [Bounded parsing](../../apps/api/src/lecturepilot/bounded_processing.py)
  defaults to two worker processes, 768 MiB address-space limit per worker on
  Linux, one task per child. Source ingestion competes with learning traffic.
- [Compiler](../../apps/latex-compiler/src/lecturepilot_latex_compiler/server.py)
  serializes compilation. The [converter image](../../apps/document-converter/Dockerfile)
  limits HTTP concurrency to 4; neither workload belongs in a read-only capacity
  estimate. OCR is an additional explicitly configured service.

## Translate measurements into users without inventing a number

Keep four distinct quantities in the presentation:

1. **Registered learners:** durable accounts and stored work; mostly a storage
   and retention question, not an in-memory session count.
2. **Actively studying learners:** learners currently reading or answering;
   most spend time thinking rather than sending requests.
3. **Concurrent HTTP requests:** work in flight, including waiting tutor streams.
4. **Concurrent inference calls:** provider work, currently bounded separately.

For a measured workload, let `I` be seconds between turns per active learner,
`k` mean provider calls per turn including retries, `t` mean provider seconds
per call, and `h` a deliberately chosen headroom factor, e.g. 0.5. An average
same-model planning bound is:

```txt
active learners <= h * 3 * I / (k * t)
```

Also require aggregate calls/minute and tokens/minute below actual provider
quotas, HTTP streams below the request limit, and acceptable observed latency,
error rates, CPU, RAM, disk I/O and queueing. A more precise heterogeneous-turn
calculation uses measured total provider-slot seconds per turn instead of
`k * t`. A burst where a class submits together can fail the latency target even
when this average bound looks comfortable.

For read-heavy activity, use measured sustainable requests/second at the chosen
latency/error target, divided by the measured requests/second per active
learner. Do not extrapolate from `/health`, one cached file, development auth,
or a few loopback requests to production learner capacity.

**Illustration only, not a capacity result:** `I=60`, `k=2`, `t=10`, `h=0.5`
gives 4.5 active chat learners at that cadence; `k=1`, `t=2` gives 45. This
tenfold difference on the same VM explains why a user-count claim needs real
provider timings and trace counts. These input values are hypothetical.

## Storage and total cost

Shared published content amortizes across enrolled students. Learner overlays,
generated images, practice-exam PDFs, retained private sources, event tables,
logs and backups still grow. Estimate:

```txt
usable disk = disk - OS/images/build cache - database - shared course assets
              - logs - operational reserve
stored learners <= usable disk / measured retained bytes per learner
total monthly cost = VM + IP + backups + storage/egress + model usage
                     + optional image/OCR services + operational costs
```

Measure p50/p95 per-learner retained bytes and actual course-source sizes;
do not assume all learners upload identical amounts. Reserve deployment space:
the current [deployment notes](../self-hosting.md) require at least 4 GiB free
before image builds. Database and files must be restored together; a same-disk
copy is not an off-host backup. No model-price estimate is asserted here.

## Acceptance gate before using a student-capacity number

- Test the actual resource budget and runtime image, including Postgres,
  session auth, writes and streaming; report CPU architecture and host limits.
- Separate prepared-course learning traffic from professor uploads/generation.
- Use realistic think time plus synchronized bursts, several users and courses,
  warm and cold caches, sustained load and a recovery period.
- Report p50/p95/p99 latency, errors including 429/503, stream completion,
  provider queue/call times, request/call/token counts, RSS, CPU, I/O and disk.
- Predeclare headroom and a service target. No OOM, corrupt state or increasing
  queue is acceptable, even if a short average-throughput result looks strong.
- Rehearse restart and matched backup restore; a single cheap VM has no
  application-level redundancy. Institutional privacy/security approval remains
  a separate gate from speed or cost.

Presentation-safe conclusion before those tests: **The architecture shares
prepared learning content and delegates inference, keeping interactive hosting
light. Full-stack low-cost deployment and a specific student count still depend
on measured helper-service peaks, authenticated workload and provider limits.**

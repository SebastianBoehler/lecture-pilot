# Resource-capped authenticated read measurements

Date: 2026-09-04. This is a local prepared-course read benchmark, **not a test
on a rented VPS and not a measured AI-tutoring capacity claim**. Current vendor
prices and the full-stack resource envelope are in
[the capacity sources note](2026-09-04-vps-capacity-sources.md).

## Reproducible scope

- API image `lecturepilot-api:readiness-20260904`, image ID
  `sha256:702b02ade6a9f2c867810e5028a69cdd7e22e7370671c768e77da57e75b8fa6e`.
  It contains base commit `8e656e2` plus local persistence fixes, not a pristine
  checkout; later provider-response changes were not in this image.
- Apple M4 Max host, macOS 26.6.2; Docker Linux `aarch64` VM reported 14 CPUs and
  23,842,430,976 bytes of RAM. Container resource caps do not emulate the CPU
  speed, contention, disk latency or network of a shared Hetzner/DigitalOcean VM.
- API capped at one CPU and initially 768 MiB RAM, with swap disabled. Postgres
  16 Alpine capped at 0.5 CPU and 512 MiB RAM. These are separate container caps,
  not a single one-CPU/one-GB machine budget.
- Production application mode, real `SessionStore` cookies, native identity
  repository, migrated disposable Postgres and normal request rate limits.
  No provider credentials were supplied and no model calls were made.
- Forty explicitly synthetic identities, isolated database
  `lecturepilot_capacity_pytest`. No real account or university login was used.
- A private isolated copy of the prepared `martius-ml` course: 2,109 files and
  307,803,127 bytes after fixture preparation. Only this copied workspace's
  access audience was set to authenticated university members, because synthetic
  accounts are not real Alma enrollments. Published content and release dates
  were preserved. This does not benchmark enrolled-only course matching.
- One course, fresh learner progress, warm-cache request scenarios; not an
  institution-wide catalog, mature progress history or cold-cache workload.
- No HTTPS gateway, static web, TeX compiler or document converter in this run.
  Thus production `/ready` and the full Compose dependency topology were not
  verified. These helper services remain mandatory in current deployment config.
- The local development app and unrelated Docker activity also existed on the
  host. Main-agent heavy tests were paused after the initial warm-up runs;
  low-CPU live provider checks continued. This is not an isolated physical host.

## Workload and controls

Each client cycles through equal shares of five real GET routes:

1. Published lecture canvas.
2. Learner lesson state, including published-revision binding validation.
3. Course review queue.
4. Lecture list and release/publication visibility.
5. Authenticated account profile (`/me`).

Clients normally wait exactly two seconds **after** each response; their initial
offsets are staggered over two seconds. This is a closed-loop active-read workload,
not an open-loop fixed arrival rate or a model of human tutoring cadence. It
includes native auth/database work and any normal GET-side cache/session effects,
but no mutating API endpoints, new learner answers, generated content or assets.

Each run first checks unauthenticated canvas access returns 401 and every
authenticated route returns 200. The final harness additionally verifies `/me`
returns the expected synthetic identity, and uses explicit per-request cookies
to avoid sharing a client cookie jar between simulated learners.

HTTP latency is client-observed round trip. Percentiles use nearest rank;
timeouts and non-200 statuses count as requests, not omitted samples. Docker
statistics were sampled approximately every five seconds. Reported memory/CPU
maxima are **sampled maxima**, not guaranteed true peaks or process RSS.

## Measurement results

The early 1-, 5- and 15-client runs included monitor shutdown time in their
throughput denominator; retain their raw results as exploratory measurements.
The final harness excludes monitor shutdown but includes requests still in
flight after its arrival window. No historical result files are rewritten.

| Scenario                                                       | Requests | Achieved req/s |      p50 |      p95 |      p99 | Errors |
| -------------------------------------------------------------- | -------: | -------------: | -------: | -------: | -------: | -----: |
| 15 clients, 2 s think, 120 s window, 768 MiB API (exploratory) |      878 |           7.12 |    33 ms |   122 ms |   169 ms |      0 |
| 30 clients, 2 s think, 120 s window, 768 MiB API               |    1,748 |          14.57 |    38 ms |   158 ms |   227 ms |      0 |
| 30 clients, zero think, 30 s arrival burst, 768 MiB API        |      883 |          28.80 | 1,139 ms | 2,002 ms | 2,130 ms |      0 |

The burst includes request drain to 30.665 seconds. It is an intentional
saturation probe, not an acceptable-UX capacity result: almost double throughput
increased p95 latency more than twelvefold. The normal run demonstrates thirty
simulated **active read clients**, not thirty continuously in-flight requests.

| Sampled maximum           | 30 clients with think time | 30-client burst |
| ------------------------- | -------------------------: | --------------: |
| API memory                |                  140.0 MiB |       164.6 MiB |
| API CPU (100% = one core) |                     42.77% |         101.93% |
| Postgres memory           |                  69.90 MiB |       73.91 MiB |
| Postgres CPU              |                      1.59% |           2.51% |

CPU saturation, rather than exhausted RAM, was the observed limit in this read
probe. This does not identify the next bottleneck for tutoring or ingestion.

Reducing the API cap to **512 MiB**, alongside the 512 MiB Postgres container,
and disabling swap for both still passed the two-minute 30-client comparison:
**1,756 reads, 14.63 req/s, p50 33 ms, p95 128 ms, p99 163 ms, zero HTTP or
identity errors**. The arrival window plus final request drain was 120.056 s.
Maximum sampled API memory was 170.2 MiB and CPU 43.25%; Postgres was 74.1 MiB
and 1.07%. The lower latency is run-to-run variation, not evidence that lowering
the memory ceiling speeds the application up. The run followed the burst with
already-warm caches. Neither container OOMed or restarted during load.

A subsequent explicit API restart at 512 MiB passed a ten-second authenticated
smoke with the persisted synthetic sessions. This is not a database/filesystem
backup restore or an entirely cold-cache benchmark. Published canvas files in
the copied fixture remained byte-identical to the original after the runs.

Read-only startup does not load every tutoring dependency. A separate, no-network
container imported LiteLLM without credentials or inference under a 512 MiB cap:
1.046 seconds and 196,908 KiB maximum RSS (about 192.3 MiB) for that standalone
process. Its remote price-map fetch was blocked by the disabled network. Do not
add this RSS to API Docker memory as though they were identical, disjoint
measurements, or mistake the import for a real tutor-turn memory test.

## What a presentation may conclude

Presentation-safe result: **Thirty active read clients completed about fifteen
authenticated requests per second with p95 below 160 ms in resource-capped local
tests. This demonstrates a small read-service footprint, not thirty simultaneous
AI conversations on a $5 VPS.**

This workload separates the inexpensive prepared-content service from paid
inference and professor ingestion. A successful low-memory read test does not
demonstrate that all services fit together during conversion/generation, nor
that the provider can answer the same number of concurrent learners.

The architecture currently caps same-model provider requests at three per event
loop. Use actual provider seconds, calls per turn, tokens, quotas and student
think time for a separate AI-throughput estimate. Model prices and API bills
are additional to VPS rent. Registered accounts, active readers, open requests
and active inference calls must not be reported as one interchangeable number.

## Reuse and verification

The harness rejects non-loopback targets, redirects and non-synthetic session
fixtures. The fixture provisioner only accepts a specifically named disposable
local Postgres database and destinations below this repository's ignored
`output/` directory. It does not truncate a database or mutate the source course.

With the isolated Docker API and DB running and `DATABASE_URL` set explicitly
to that disposable database, provision and measure using:

The completed run's private workspace was subsequently archived to
`output/demo-cleanup-2026-09-04/capacity-test-workspace/`. Restore a copy to the
path below before reproducing this command; aggregated measurements remain in
their original output directory.

```bash
.venv/bin/python scripts/seed_read_capacity.py \
  --workspace output/capacity-2026-09-04/workspace \
  --output output/capacity-2026-09-04/new-sessions.json --users 40
.venv/bin/python scripts/benchmark_read_capacity.py \
  --sessions output/capacity-2026-09-04/new-sessions.json \
  --users 30 --duration 120 --think-seconds 2 \
  --output output/capacity-2026-09-04/new-results.json
.venv/bin/python -m unittest discover -s scripts -p test_read_capacity.py
```

Five harness/guard regression tests pass. Python formatting and lint pass.
Raw aggregated results and private synthetic session fixtures remain ignored
under `output/capacity-2026-09-04/`; session tokens are saved mode 0600 and never
printed. No provider keys, lecture content or learner text are in result JSON.

Cleanup: the temporary API was stopped and the disposable auto-remove Postgres
container and its ephemeral database were removed on stop. The database contains
only reproducible synthetic accounts/sessions. Private copied files and raw
measurements are retained locally; the runtime image and Docker network remain
available. No original course or learner workspace was changed.

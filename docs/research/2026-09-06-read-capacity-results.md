# Bounded local read capacity — 6 September 2026

Repeated the frozen 4 September image to reproduce and extend the earlier
[read benchmark](2026-09-04-capacity-measurements.md). This does not benchmark
today's working-tree changes or a rented VPS.

| Active readers | Requests | Requests/s |    p50 |      p95 |      p99 | HTTP/identity errors |
| -------------: | -------: | ---------: | -----: | -------: | -------: | -------------------: |
|             30 |      877 |     14.617 |  37 ms |   138 ms |   169 ms |                    0 |
|             60 |    1,500 |     24.441 | 132 ms | 1,924 ms | 2,698 ms |                    0 |

Each arrival window was 60 seconds; the second run drained until 61.373 seconds.
Clients waited two seconds after each response and were initially staggered.
The five authenticated GET routes, identity checks, normal rate limits and
unauthenticated 401 control were unchanged from the earlier harness.

The 30-reader result reproduces the earlier responsive case. Doubling readers
increased throughput but severely worsened tail latency. Neither is a maximum
capacity estimate or evidence for simultaneous AI tutoring. One run per level
does not provide confidence intervals or long-duration reliability evidence.

## Environment and resources

- Apple M4 Max, macOS 26.6.2; Docker Linux aarch64, 14 CPUs and
  23,842,430,976 bytes available to the VM. Other local activity remained present.
- API: one CPU, 512 MiB RAM; Postgres: half a CPU, 512 MiB RAM.
  Swap disabled for both. These are separate container budgets.
- Image `lecturepilot-api:readiness-20260904`, exact ID
  `sha256:702b02ade6a9f2c867810e5028a69cdd7e22e7370671c768e77da57e75b8fa6e`.
  Its source provenance is documented in the earlier report.
- Fresh disposable Postgres, migrations from that image, 100 synthetic accounts;
  copied archived course under ignored output. No real account or source changed.
- Production session-auth mode, localhost port 58009. No model keys or calls,
  HTTPS gateway, static web, compiler or converter workload in the measured stack.
- Five harness guard tests passed before execution. No OOM or container restart.

| Sampled maximum          | 30 readers | 60 readers |
| ------------------------ | ---------: | ---------: |
| API memory               |  138.7 MiB |  183.2 MiB |
| API CPU, 100% = one core |     54.08% |    102.01% |
| DB memory                |  44.63 MiB |  49.65 MiB |
| DB CPU                   |      1.83% |      5.68% |

API CPU saturation coincided with the latency increase. Sampled maxima are not
guaranteed peaks. Runs used one prepared course and warm application/file caches;
they do not model a large catalog or mature student histories.

## Evidence and reproduction

Private aggregate JSON is retained in `output/capacity-2026-09-06/`:
`30-readers.json`, `60-readers.json`, `environment.json`,
`completion-state.json`, and `storage.json`. Session fixtures remain private.
The benchmark commands, after isolated provisioning as in the earlier report:

```bash
.venv/bin/python scripts/benchmark_read_capacity.py \
  --base-url http://127.0.0.1:58009 \
  --sessions output/capacity-2026-09-06/sessions.json \
  --users 30 --duration 60 --think-seconds 2 \
  --containers lecturepilot-capacity-api-20260906 lecturepilot-capacity-db \
  --output output/capacity-2026-09-06/30-readers.json
```

The second command changed users to 60 and output to `60-readers.json`.
Reproduction needs fresh sessions, provisioning and unused output filenames.
Both temporary containers and their network were removed after measurement;
their ephemeral synthetic database was discarded, copied files retained.
The previous stopped benchmark container and unrelated services were untouched.

Interpretation and storage arithmetic: [presentation economics](2026-09-06-presentation-economics.md).

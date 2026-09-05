"""Loopback-only authenticated read benchmark; never calls models or writes API state."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import json
import math
from pathlib import Path
import platform
import subprocess
import time
from urllib.parse import urlsplit

import httpx


PATHS = (
    "/courses/martius-ml/lectures/lecture-01/canvas",
    "/courses/martius-ml/lectures/lecture-01/learner-state",
    "/courses/martius-ml/review-queue",
    "/courses/martius-ml/lectures",
    "/me",
)


def local_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("Only plain HTTP loopback targets are permitted.")
    if (
        parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("Target must be a bare loopback origin.")
    return value.rstrip("/")


def percentile(values: list[float], fraction: float) -> float:
    return (
        round(sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)], 2)
        if values
        else 0
    )


def summary(rows: list[dict], elapsed: float) -> dict:
    durations = [row["ms"] for row in rows]
    return {
        "requests": len(rows),
        "requests_per_second": round(len(rows) / elapsed, 3),
        "p50_ms": percentile(durations, 0.5),
        "p95_ms": percentile(durations, 0.95),
        "p99_ms": percentile(durations, 0.99),
        "status_counts": dict(Counter(str(row["status"]) for row in rows)),
        "response_bytes_total": sum(row["bytes"] for row in rows),
    }


def docker_sample(containers: list[str]) -> list[dict]:
    result = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", "{{json .}}", *containers],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


async def run(args: argparse.Namespace) -> dict:
    tokens_data = json.loads(args.sessions.read_text())
    if tokens_data.get("synthetic") is not True:
        raise ValueError("Only explicitly synthetic session fixtures are accepted.")
    tokens = tokens_data["tokens"]
    if len(tokens) < args.users:
        raise ValueError("Not enough distinct synthetic sessions.")
    rows: list[dict] = []
    samples: list[dict] = []
    limits = httpx.Limits(max_connections=100, max_keepalive_connections=100)
    transport = httpx.AsyncHTTPTransport(retries=0, limits=limits)
    async with httpx.AsyncClient(
        base_url=args.base_url,
        transport=transport,
        limits=limits,
        timeout=30,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        unauthorized = await client.get(PATHS[0])
        if unauthorized.status_code != 401:
            raise ValueError("Unauthenticated canvas request must return 401.")
        for path in PATHS:
            response = await client.get(
                path, headers={"Cookie": f"lecturepilot_session={tokens[0]}"}
            )
            if response.status_code != 200:
                raise ValueError(
                    f"Preflight failed for {path}: HTTP {response.status_code}"
                )
            if path.endswith("/lectures") and not response.json():
                raise ValueError("Prepared lecture list is empty.")
        start = time.perf_counter()
        deadline = start + args.duration

        async def learner(index: int) -> None:
            await asyncio.sleep(index * args.think_seconds / args.users)
            step = index
            while time.perf_counter() < deadline:
                path = PATHS[step % len(PATHS)]
                begun = time.perf_counter()
                try:
                    response = await client.get(
                        path,
                        headers={"Cookie": f"lecturepilot_session={tokens[index]}"},
                    )
                    status, length = response.status_code, len(response.content)
                    if path == "/me" and status == 200:
                        if (
                            response.json().get("username")
                            != f"capacity-synthetic-{index:03d}"
                        ):
                            status = "identity_mismatch"
                except httpx.HTTPError as exc:
                    status, length = type(exc).__name__, 0
                rows.append(
                    {
                        "route": path,
                        "ms": (time.perf_counter() - begun) * 1000,
                        "status": status,
                        "bytes": length,
                        "completed_seconds": time.perf_counter() - start,
                    }
                )
                step += 1
                await asyncio.sleep(args.think_seconds)

        async def monitor() -> None:
            while time.perf_counter() < deadline:
                sample = await asyncio.to_thread(docker_sample, args.containers)
                samples.append(
                    {
                        "elapsed_seconds": round(time.perf_counter() - start, 2),
                        "containers": sample,
                    }
                )
                await asyncio.sleep(3)

        await asyncio.gather(monitor(), *(learner(i) for i in range(args.users)))
        # Do not dilute throughput with the monitor's shutdown sleep. Include
        # requests still in flight at the end of the requested arrival window.
        elapsed = max(args.duration, max(row["completed_seconds"] for row in rows))
    return {
        "scope": "loopback session-auth prepared-course reads; no inference, TLS, uploads or mutating endpoints",
        "client_platform": platform.platform(),
        "users": args.users,
        "requested_duration_seconds": args.duration,
        "elapsed_seconds": round(elapsed, 3),
        "think_seconds_after_each_response": args.think_seconds,
        "auth_negative_control": unauthorized.status_code,
        "overall": summary(rows, elapsed),
        "routes": {
            path: summary([r for r in rows if r["route"] == path], elapsed)
            for path in PATHS
        },
        "docker_samples": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", type=local_url, default="http://127.0.0.1:58001")
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--duration", type=int, default=120)
    parser.add_argument("--think-seconds", type=float, default=2)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--containers",
        nargs="+",
        default=["lecturepilot-capacity-api", "lecturepilot-capacity-db"],
    )
    args = parser.parse_args()
    if (
        not 1 <= args.users <= 100
        or not 10 <= args.duration <= 600
        or not math.isfinite(args.think_seconds)
        or not 0 <= args.think_seconds <= 60
    ):
        parser.error(
            "users 1..100, duration 10..600 and finite think time 0..60 required"
        )
    if any(not name.startswith("lecturepilot-capacity-") for name in args.containers):
        parser.error("Only explicitly named capacity containers may be inspected")
    output_root = Path(__file__).resolve().parents[1] / "output"
    if not args.output.resolve().is_relative_to(output_root) or args.output.exists():
        parser.error("Use a new result file below output")
    result = asyncio.run(run(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2)
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key not in {"docker_samples", "routes"}
            }
        )
    )


if __name__ == "__main__":
    main()

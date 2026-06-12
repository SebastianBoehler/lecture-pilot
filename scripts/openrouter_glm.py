#!/usr/bin/env python3
"""Run a GLM design prompt through OpenRouter using the repo-local .env key."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "z-ai/glm-5.1"
DEFAULT_MAX_TOKENS = 1600


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def dotenv_value(path: Path, target: str) -> str | None:
    if not path.exists():
        return None
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.removeprefix("export ").strip()
        if key == target:
            return value.strip().strip('"').strip("'")
    return None


def openrouter_key() -> str:
    env_key = dotenv_value(repo_root() / ".env", "OPENROUTER_API_KEY")
    key = env_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set in .env or the shell.")
    return key


def request_completion(prompt: str, model: str, max_tokens: int) -> str:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You produce concise, implementation-ready product UI specs.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.35,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {openrouter_key()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/SebastianBoehler/lecture-pilot",
            "X-Title": "LecturePilot",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8")[:500]
        raise RuntimeError(f"OpenRouter request failed with HTTP {error.code}: {detail}") from error

    message = data["choices"][0]["message"]
    content = message.get("content")
    if not content:
        finish_reason = data["choices"][0].get("finish_reason")
        raise RuntimeError(f"OpenRouter returned no content. finish_reason={finish_reason}")
    return content


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    args = parser.parse_args()
    prompt = sys.stdin.read().strip()
    if not prompt:
        print("Prompt is required on stdin.", file=sys.stderr)
        return 2
    try:
        print(request_completion(prompt, args.model, args.max_tokens))
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
from collections.abc import Mapping
import os
from pathlib import Path
import re

from dotenv import dotenv_values

from lecturepilot.release_info import release_info


_DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?=[a-z0-9-]{2,63}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)
_PROVIDER_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "google": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}
_PLACEHOLDERS = {"change-me", "changeme", "password", "replace-me", "secret"}
_URL_SAFE_PASSWORD = re.compile(r"^[A-Za-z0-9._~-]+$")
_COMMIT_SHA = re.compile(r"^[0-9a-fA-F]{7,64}$")


def validate_production_environment(
    env: Mapping[str, str | None],
    *,
    build_commit_sha: str | None = None,
) -> list[str]:
    errors: list[str] = []
    domain = _value(env, "LECTUREPILOT_DOMAIN").lower()
    if not _DOMAIN_PATTERN.fullmatch(domain):
        errors.append("LECTUREPILOT_DOMAIN must be a public DNS hostname without a scheme or path.")

    password = _value(env, "LECTUREPILOT_POSTGRES_PASSWORD")
    if len(password) < 24 or password.casefold() in _PLACEHOLDERS:
        errors.append("LECTUREPILOT_POSTGRES_PASSWORD must contain at least 24 random characters.")
    elif not _URL_SAFE_PASSWORD.fullmatch(password):
        errors.append(
            "LECTUREPILOT_POSTGRES_PASSWORD must use URL-safe characters because Compose embeds it in DATABASE_URL."
        )

    model = _value(env, "LECTUREPILOT_MODEL")
    if "/" not in model:
        errors.append("LECTUREPILOT_MODEL must include an explicit provider prefix.")
    allowed_models = {
        item.strip()
        for item in _value(env, "LECTUREPILOT_ALLOWED_MODELS").split(",")
        if item.strip()
    }
    if not allowed_models or model not in allowed_models:
        errors.append("LECTUREPILOT_ALLOWED_MODELS must explicitly include LECTUREPILOT_MODEL.")

    provider = model.split("/", 1)[0].lower() if "/" in model else ""
    provider_key = _PROVIDER_KEYS.get(provider)
    if provider_key is None:
        errors.append("LECTUREPILOT_MODEL uses an unsupported provider prefix.")
    elif not _value(env, provider_key):
        errors.append(f"{provider_key} is required for the configured production model.")

    trace_content = _value(env, "LECTUREPILOT_TRACE_CONTENT") or "metadata"
    if trace_content not in {"metadata", "redacted"}:
        errors.append("LECTUREPILOT_TRACE_CONTENT must be metadata or redacted in production.")

    expected_commit_sha = _value(env, "LECTUREPILOT_COMMIT_SHA").lower()
    if not _COMMIT_SHA.fullmatch(expected_commit_sha):
        errors.append("LECTUREPILOT_COMMIT_SHA must be the deployed Git commit SHA.")
    elif build_commit_sha is not None and expected_commit_sha != build_commit_sha.lower():
        errors.append("The API image revision does not match LECTUREPILOT_COMMIT_SHA.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate LecturePilot production configuration.")
    parser.add_argument("--env-file", default=".env", type=Path)
    parser.add_argument("--require-build-identity", action="store_true")
    args = parser.parse_args()
    values = {
        key: value for key, value in dotenv_values(args.env_file).items() if value is not None
    }
    values.update(os.environ)
    errors = validate_production_environment(
        values,
        build_commit_sha=release_info().commit_sha if args.require_build_identity else None,
    )
    if args.env_file.is_file() and args.env_file.stat().st_mode & 0o077:
        errors.append(f"{args.env_file} must not be readable or writable by group/other users.")
    if errors:
        print("Production preflight failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Production preflight passed.")
    return 0


def _value(env: Mapping[str, str | None], name: str) -> str:
    return (env.get(name) or "").strip()


if __name__ == "__main__":
    raise SystemExit(main())

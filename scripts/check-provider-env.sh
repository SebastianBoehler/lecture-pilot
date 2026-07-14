#!/usr/bin/env bash
set -euo pipefail

model="${LECTUREPILOT_MODEL:-gemini/gemini-3.1-flash-lite}"
if [[ "$model" != */* ]]; then
  echo "LECTUREPILOT_MODEL must include a provider prefix: ${model}" >&2
  exit 1
fi

provider="${model%%/*}"
case "$provider" in
  gemini | google)
    key_env="GEMINI_API_KEY"
    ;;
  openai)
    key_env="OPENAI_API_KEY"
    ;;
  openrouter)
    key_env="OPENROUTER_API_KEY"
    ;;
  *)
    echo "Unsupported provider prefix in LECTUREPILOT_MODEL: ${provider}" >&2
    exit 1
    ;;
esac

if [[ -z "${!key_env:-}" ]]; then
  echo "${key_env} is required for LECTUREPILOT_MODEL=${model}." >&2
  exit 1
fi

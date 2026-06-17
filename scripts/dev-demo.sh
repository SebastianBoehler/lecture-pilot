#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

api_port="${LECTUREPILOT_API_PORT:-8001}"
api_pid=""
web_pid=""

cleanup() {
  if [[ -n "$web_pid" ]]; then
    kill "$web_pid" 2>/dev/null || true
  fi
  if [[ -n "$api_pid" ]]; then
    kill "$api_pid" 2>/dev/null || true
  fi
}
trap cleanup INT TERM EXIT

set -a
[[ -f .env ]] && source .env
set +a
if [[ -z "${OPENROUTER_API_KEY:-}" && -f ../sunderlabs/.env.local ]]; then
  OPENROUTER_API_KEY="$(python - <<'PY'
from pathlib import Path
for line in Path("../sunderlabs/.env.local").read_text(errors="ignore").splitlines():
    if line.startswith("OPENROUTER_API_KEY="):
        print(line.split("=", 1)[1].strip().strip('"').strip("'"))
        break
PY
)"
  export OPENROUTER_API_KEY
fi
if [[ -z "${LECTUREPILOT_MODEL:-}" \
  || "$LECTUREPILOT_MODEL" == "gemini/gemini-3.1-flash-lite" \
  || "$LECTUREPILOT_MODEL" == "openrouter/google/gemini-3.1-flash-lite" ]]; then
  export LECTUREPILOT_MODEL="openrouter/openai/gpt-oss-120b:nitro"
fi

if curl -fsS "http://127.0.0.1:${api_port}/health" >/dev/null 2>&1; then
  if curl -fsS "http://127.0.0.1:${api_port}/courses" \
    -H 'X-User-Id: professor-demo' \
    -H 'X-Tenant-Id: tenant-tuebingen' \
    -H 'X-User-Role: professor' >/dev/null 2>&1; then
    echo "LecturePilot API already listening on http://127.0.0.1:${api_port}"
  else
    echo "Port ${api_port} is in use, but it is not the LecturePilot API." >&2
    echo "Stop that process or run with LECTUREPILOT_API_PORT=<free-port> npm run dev:demo" >&2
    exit 1
  fi
elif lsof -nP -iTCP:"$api_port" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port ${api_port} is already in use by a non-LecturePilot process." >&2
  echo "Stop that process or run with LECTUREPILOT_API_PORT=<free-port> npm run dev:demo" >&2
  exit 1
else
  source .venv/bin/activate
  uvicorn lecturepilot.app:app --app-dir apps/api/src --reload --host 127.0.0.1 --port "$api_port" &
  api_pid="$!"
fi

VITE_API_BASE_URL="http://127.0.0.1:${api_port}" \
  npm run dev --workspace apps/web &
web_pid="$!"

wait "$web_pid"

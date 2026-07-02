#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

set -a
[[ -f .env ]] && source .env
set +a

api_port="${LECTUREPILOT_API_PORT:-8001}"
web_port="${LECTUREPILOT_WEB_PORT:-5173}"
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

stop_repo_process_on_port() {
  local port="$1"
  local label="$2"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  [[ -z "$pids" ]] && return 0
  local commands
  commands="$(ps -o command= -p $(echo "$pids" | tr '\n' ' ') 2>/dev/null || true)"
  if [[ "$commands" == *"$root"* || "$commands" == *"lecturepilot.app:app"* ]]; then
    echo "Stopping stale LecturePilot ${label} on port ${port}"
    kill $pids 2>/dev/null || true
    for _ in {1..40}; do
      if ! lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
        return 0
      fi
      sleep 0.25
    done
  fi
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port ${port} is already in use by a non-demo ${label} process." >&2
    echo "Stop that process or choose another port." >&2
    exit 1
  fi
}

stop_repo_process_on_port "$api_port" "API"
stop_repo_process_on_port "$web_port" "web server"

if lsof -nP -iTCP:"$api_port" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port ${api_port} is already in use." >&2
  exit 1
fi
source .venv/bin/activate
uvicorn lecturepilot.app:app --app-dir apps/api/src --reload --reload-dir apps/api/src --host 127.0.0.1 --port "$api_port" &
api_pid="$!"

for _ in {1..80}; do
  if curl -fsS "http://127.0.0.1:${api_port}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done
if ! curl -fsS "http://127.0.0.1:${api_port}/health" >/dev/null 2>&1; then
  echo "LecturePilot API did not become ready on http://127.0.0.1:${api_port}" >&2
  exit 1
fi

VITE_API_BASE_URL="http://127.0.0.1:${api_port}" \
  npm run dev --workspace apps/web -- --port "$web_port" &
web_pid="$!"

wait "$web_pid"

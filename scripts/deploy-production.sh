#!/usr/bin/env bash

set -Eeuo pipefail

readonly REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly ENV_FILE="${REPOSITORY_ROOT}/.env"
readonly COMPOSE_FILE="${REPOSITORY_ROOT}/deploy/compose.yml"
readonly MIN_FREE_KB=$((1024 * 1024))
readonly RETAIN_IMAGES_FOR="168h"

compose() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

available_docker_kb() {
  local docker_root
  docker_root="$(docker info --format '{{.DockerRootDir}}')"
  df -Pk "${docker_root}" | awk 'NR == 2 { print $4 }'
}

prune_build_failures() {
  echo "Cleaning incomplete Docker build artifacts..." >&2
  docker builder prune -af >/dev/null || true
  docker image prune -f >/dev/null || true
}

ensure_build_space() {
  local available_kb
  available_kb="$(available_docker_kb)"
  if ((available_kb >= MIN_FREE_KB)); then
    return
  fi

  echo "Docker storage is low; removing unused build cache and images..." >&2
  docker builder prune -af >/dev/null
  docker image prune -af >/dev/null
  available_kb="$(available_docker_kb)"
  if ((available_kb < MIN_FREE_KB)); then
    echo "Deployment stopped before building: Docker needs at least 1 GiB free." >&2
    echo "Available: $((available_kb / 1024)) MiB." >&2
    exit 1
  fi
}

on_exit() {
  local status=$?
  if ((status != 0)); then
    prune_build_failures
  fi
  exit "${status}"
}

main() {
  cd "${REPOSITORY_ROOT}"
  [[ -f "${ENV_FILE}" ]] || {
    echo "Missing ${ENV_FILE}." >&2
    exit 1
  }

  export LECTUREPILOT_COMMIT_SHA
  LECTUREPILOT_COMMIT_SHA="$(git rev-parse HEAD)"
  [[ -z "$(git status --porcelain)" ]] || {
    echo "Deployment stopped: the checkout has uncommitted changes." >&2
    exit 1
  }

  trap on_exit EXIT
  compose config --quiet
  ensure_build_space

  echo "Building API ${LECTUREPILOT_COMMIT_SHA}..."
  compose build api
  echo "Building web ${LECTUREPILOT_COMMIT_SHA}..."
  compose build web

  echo "Checking the application against the running infrastructure..."
  compose run --rm --no-deps preflight
  compose run --rm --no-deps migrate

  echo "Starting the verified application images..."
  compose up -d --no-deps --no-build api web

  trap - EXIT
  docker image prune -af --filter "until=${RETAIN_IMAGES_FOR}" >/dev/null
  docker builder prune -af >/dev/null
  compose ps
}

main "$@"

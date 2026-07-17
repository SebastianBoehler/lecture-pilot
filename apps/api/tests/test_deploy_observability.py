from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_compose_persists_metadata_logs_and_uses_readiness_probe() -> None:
    compose = yaml.safe_load((REPO_ROOT / "deploy" / "compose.yml").read_text())
    api = compose["services"]["api"]
    compiler = compose["services"]["latex-compiler"]

    assert compose["x-api-environment"]["LECTUREPILOT_METADATA_LOG_PATH"] == (
        "/app/logs/api-metadata.jsonl"
    )
    assert "lecturepilot-api-logs:/app/logs" in api["volumes"]
    healthcheck = " ".join(api["healthcheck"]["test"])
    assert "('health', 'ready')" in healthcheck
    assert compiler["environment"]["LECTUREPILOT_METADATA_LOG_PATH"] == (
        "/app/logs/compiler-metadata.jsonl"
    )
    assert "lecturepilot-compiler-logs:/app/logs" in compiler["volumes"]
    assert {"lecturepilot-api-logs", "lecturepilot-compiler-logs"} <= set(compose["volumes"])


def test_production_disables_duplicate_access_logs() -> None:
    dockerfile = (REPO_ROOT / "apps" / "api" / "Dockerfile").read_text()

    assert "--no-access-log" in dockerfile
    assert "mkdir -p /app/logs" in dockerfile


def test_postgres_collects_normalized_query_statistics_without_statement_logging() -> None:
    compose = yaml.safe_load((REPO_ROOT / "deploy" / "compose.yml").read_text())
    command = compose["services"]["db"]["command"]
    migration = (
        REPO_ROOT / "apps/api/migrations/versions/20260715_0008_query_statistics.py"
    ).read_text()

    assert "shared_preload_libraries=pg_stat_statements" in command
    assert "track_io_timing=on" in command
    assert all("log_statement" not in value for value in command)
    assert all("log_min_duration_statement" not in value for value in command)
    assert "CREATE EXTENSION IF NOT EXISTS pg_stat_statements" in migration


def test_web_server_rejects_obvious_wordpress_probes_before_spa_fallback() -> None:
    config = (REPO_ROOT / "apps" / "web" / "nginx.conf").read_text()

    probe_rule = config.index("wp(?:-(?:admin|content|includes|json))?")
    spa_fallback = config.index("try_files $uri $uri/ /index.html")
    assert probe_rule < spa_fallback
    assert "xmlrpc" in config[probe_rule:spa_fallback]
    assert "content|includes|json" in config[probe_rule:spa_fallback]
    assert "return 404" in config[probe_rule:spa_fallback]


def test_production_images_do_not_rebuild_stock_caddy() -> None:
    dockerfile = (REPO_ROOT / "deploy" / "Caddy.Dockerfile").read_text()

    assert dockerfile.startswith("FROM caddy:2.11.4-alpine")
    assert "xcaddy" not in dockerfile
    assert "builder" not in dockerfile


def test_successful_deploy_discards_build_cache_but_retains_rollback_images() -> None:
    deploy_script = (REPO_ROOT / "scripts" / "deploy-production.sh").read_text()

    assert 'readonly RETAIN_IMAGES_FOR="168h"' in deploy_script
    assert 'docker image prune -af --filter "until=${RETAIN_IMAGES_FOR}"' in deploy_script
    assert "docker builder prune -af >/dev/null" in deploy_script
    assert "docker builder prune -af --filter" not in deploy_script

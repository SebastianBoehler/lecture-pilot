FROM python:3.12-slim

ARG LECTUREPILOT_COMMIT_SHA
LABEL org.opencontainers.image.revision="${LECTUREPILOT_COMMIT_SHA}"

WORKDIR /app

COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/api/requirements.lock apps/api/requirements.lock
COPY apps/api/src apps/api/src
COPY apps/api/alembic.ini apps/api/alembic.ini
COPY apps/api/migrations apps/api/migrations
COPY README.md README.md

RUN python -c 'import pathlib,re,sys; value=sys.argv[1].lower(); re.fullmatch(r"[0-9a-f]{7,64}", value) or sys.exit("LECTUREPILOT_COMMIT_SHA must be a Git commit SHA"); pathlib.Path("apps/api/src/lecturepilot/_build_commit.txt").write_text(value + "\n", encoding="ascii")' "$LECTUREPILOT_COMMIT_SHA"

RUN pip install --no-cache-dir -c apps/api/requirements.lock -e "apps/api[agent,tuebingen]"

RUN useradd --create-home --uid 10001 lecturepilot \
    && mkdir -p /app/logs /app/storage \
    && chown -R lecturepilot:lecturepilot /app/logs /app/storage

USER 10001:10001

EXPOSE 8000
CMD ["uvicorn", "lecturepilot.app:app", "--app-dir", "apps/api/src", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=172.16.0.0/12", "--limit-concurrency=100", "--backlog=512", "--timeout-keep-alive=5", "--no-server-header", "--no-access-log"]

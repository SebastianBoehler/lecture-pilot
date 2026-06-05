FROM python:3.12-slim

WORKDIR /app

COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/api/src apps/api/src
COPY README.md README.md

RUN pip install --no-cache-dir -e "apps/api[agent,tuebingen]"

EXPOSE 8000
CMD ["uvicorn", "lecturepilot.app:app", "--app-dir", "apps/api/src", "--host", "0.0.0.0", "--port", "8000"]


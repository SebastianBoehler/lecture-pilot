FROM python:3.12-slim

RUN printf '%s\n' \
      'path-exclude=/usr/share/doc/*' \
      'path-exclude=/usr/share/man/*' \
      > /etc/dpkg/dpkg.cfg.d/01_nodoc \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      fonts-dejavu-core \
      fonts-liberation \
      libreoffice-calc \
      libreoffice-core \
      libreoffice-impress \
      libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY apps/document-converter/pyproject.toml ./pyproject.toml
COPY apps/document-converter/requirements.lock ./requirements.lock
COPY apps/document-converter/src ./src
RUN pip install --no-cache-dir -c requirements.lock . \
    && groupadd --gid 10003 document-converter \
    && useradd --no-create-home --uid 10003 --gid 10003 \
      --shell /usr/sbin/nologin document-converter

USER 10003:10003
EXPOSE 8080
CMD ["uvicorn", "lecturepilot_converter.app:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8080", "--limit-concurrency", "4", "--no-server-header", "--no-access-log"]

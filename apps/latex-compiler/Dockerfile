FROM alpine:3.22 AS tectonic

ARG TARGETARCH
ARG TECTONIC_VERSION=0.16.9
ENV TECTONIC_CACHE_DIR=/var/cache/tectonic

RUN apk add --no-cache ca-certificates curl
RUN case "$TARGETARCH" in \
      amd64) \
        target=x86_64-unknown-linux-musl; \
        checksum=60b13a0826ae7ad9ce34b4a2df06bff2cfcfa6dda8a915477c0cbb84e1a4a902 ;; \
      arm64) \
        target=aarch64-unknown-linux-musl; \
        checksum=f9aa39017dbd51f111fdb93dda222178cbe51c8193508fc567b523cc74fff9c1 ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac \
    && archive="tectonic-${TECTONIC_VERSION}-${target}.tar.gz" \
    && curl -fsSLo /tmp/tectonic.tar.gz \
      "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40${TECTONIC_VERSION}/${archive}" \
    && echo "$checksum  /tmp/tectonic.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/tectonic.tar.gz -C /usr/local/bin tectonic \
    && tectonic --version

COPY apps/latex-compiler/bundle-seed.tex /tmp/bundle-seed.tex
COPY apps/latex-compiler/bundle-seeds /tmp/bundle-seeds
RUN mkdir -p /tmp/seed-online /tmp/seed-offline \
    && for source in /tmp/bundle-seed.tex /tmp/bundle-seeds/*.tex; do \
      tectonic -X compile --untrusted \
        --bundle https://data1.fullyjustified.net/tlextras-2022.0r0.tar \
        --outdir /tmp/seed-online "$source"; \
    done \
    && for source in /tmp/bundle-seed.tex /tmp/bundle-seeds/*.tex; do \
      tectonic -X compile --untrusted --only-cached \
        --bundle https://data1.fullyjustified.net/tlextras-2022.0r0.tar \
        --outdir /tmp/seed-offline "$source"; \
    done \
    && chmod -R a=rX /var/cache/tectonic

FROM python:3.12-slim

RUN printf '%s\n' \
      'path-exclude=/usr/share/doc/*' \
      'path-exclude=/usr/share/man/*' \
      > /etc/dpkg/dpkg.cfg.d/01_nodoc \
    && apt-get update \
    && apt-get install -y --no-install-recommends util-linux \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TECTONIC_CACHE_DIR=/var/cache/tectonic

COPY --from=tectonic /usr/local/bin/tectonic /usr/local/bin/tectonic
COPY --from=tectonic /var/cache/tectonic /var/cache/tectonic

WORKDIR /app
COPY apps/latex-compiler/pyproject.toml ./pyproject.toml
COPY apps/latex-compiler/src ./src
RUN pip install --no-cache-dir . \
    && groupadd --gid 10002 latex-compiler \
    && useradd --no-create-home --uid 10002 --gid 10002 \
      --shell /usr/sbin/nologin latex-compiler \
    && mkdir -p /app/logs \
    && chown latex-compiler:latex-compiler /app/logs

USER 10002:10002
EXPOSE 8080
CMD ["lecturepilot-latex-compiler"]

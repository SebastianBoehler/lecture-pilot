FROM python:3.12-slim

RUN printf '%s\n' \
      'path-exclude=/usr/share/doc/*' \
      'path-exclude=/usr/share/man/*' \
      'path-exclude=/usr/share/texlive/texmf-dist/doc/*' \
      > /etc/dpkg/dpkg.cfg.d/01_nodoc \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      texlive-fonts-extra \
      texlive-fonts-recommended \
      texlive-lang-german \
      texlive-latex-base \
      texlive-latex-extra \
      texlive-latex-recommended \
      texlive-pictures \
      texlive-science \
      util-linux \
    && rm -rf /var/lib/apt/lists/* \
    && pdflatex --version >/dev/null

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY apps/latex-compiler/pyproject.toml ./pyproject.toml
COPY apps/latex-compiler/src ./src
RUN pip install --no-cache-dir . \
    && groupadd --gid 10002 latex-compiler \
    && useradd --no-create-home --uid 10002 --gid 10002 \
      --shell /usr/sbin/nologin latex-compiler

USER 10002:10002
EXPOSE 8080
CMD ["lecturepilot-latex-compiler"]

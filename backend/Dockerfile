# syntax=docker/dockerfile:1.7
#
# Sentinel API — production image.
#
# Build context is backend/, not the repo root: it keeps the root .env and the
# frontend (node_modules, two 655KB logos) out of the context entirely rather
# than relying on .dockerignore to catch them.
#
#   docker build -t sentinel-api:0.1.0 ./backend
#
# Runtime configuration is environment only. Nothing secret is baked in — no
# ARG, no ENV default for a credential. See docs/rules/security.md.

# ---------------------------------------------------------------------------
# Stage 1 — builder. Produces a self-contained virtualenv at /opt/venv.
# ---------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS builder

# build-essential is insurance, not a known requirement: every pinned
# dependency ships a manylinux wheel for cp313 today (bcrypt and cryptography
# via abi3), but a resolver change or an arm64 build falling back to source
# would otherwise fail here. It costs nothing at runtime — this stage is
# discarded.
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Requirements before source: the install layer stays cached across every
# change that does not touch dependencies.
COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2 — runtime.
# ---------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS runtime

# psycopg[binary] bundles libpq, so no postgresql-client is needed. Nothing is
# installed here at all — the smaller the runtime, the smaller the CVE surface.

LABEL org.opencontainers.image.title="Sentinel API" \
      org.opencontainers.image.description="Operational memory and follow-up engine for founders." \
      org.opencontainers.image.source="https://github.com/Sentinel000/Sentinel-Business-Memory-Manager" \
      org.opencontainers.image.licenses="UNLICENSED"

# HOME=/tmp because the runtime user has no home directory: anything in the
# stack that reaches for ~/.cache would otherwise land on a path that does not
# exist — and under compose's read-only root filesystem, could not be created.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    HOME=/tmp \
    PORT=8000 \
    WEB_CONCURRENCY=1 \
    ENABLE_SCHEDULER=false \
    RUN_MIGRATIONS=false

# System user, no shell, no home. Created before the COPYs so ownership is set
# in one pass rather than by a chown layer that duplicates the whole tree.
RUN groupadd --system --gid 1001 sentinel && \
    useradd --system --uid 1001 --gid sentinel --no-create-home --shell /usr/sbin/nologin sentinel

WORKDIR /app

COPY --from=builder --chown=root:root /opt/venv /opt/venv

# alembic.ini uses `script_location = alembic` and `prepend_sys_path = .`, both
# relative — migrations only resolve with the working directory at /app.
COPY --chown=root:root alembic.ini ./
COPY --chown=root:root alembic ./alembic
COPY --chown=root:root app ./app
COPY --chown=root:root scripts ./scripts
COPY --chmod=0555 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Application files stay root-owned and world-readable: the process can read
# them and cannot rewrite itself.
USER sentinel

EXPOSE 8000

# python -c rather than curl: the slim image has no curl, and adding one for a
# probe would mean carrying it in production forever.
#
# Honoured by Compose and a plain Docker/VPS run. Cloud Run, ECS and Kubernetes
# ignore it and use their own probes — point those at GET /health, which is a
# liveness check that deliberately does not touch the database.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health', timeout=4).status==200 else 1)"]

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["serve"]

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/pyproject.toml
COPY packages/service/pyproject.toml packages/service/pyproject.toml
COPY packages/eval/pyproject.toml packages/eval/pyproject.toml

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace

COPY packages/core ./packages/core
COPY packages/service ./packages/service
COPY packages/eval ./packages/eval

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen


FROM python:3.12-slim-bookworm AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

WORKDIR /app

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY packages/service/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

ENTRYPOINT ["/entrypoint.sh"]

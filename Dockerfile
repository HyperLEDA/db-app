FROM python:3.13-slim AS runtime-base
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

FROM runtime-base AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
ARG SERVICE
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --extra "${SERVICE}" --no-install-project
COPY app ./app
RUN uv sync --frozen --no-dev --extra "${SERVICE}"

FROM runtime-base
ARG SERVICE
ENV SERVICE=${SERVICE}
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
COPY app ./app
COPY postgres/migrations ./postgres/migrations
COPY pyproject.toml README.md ./
ENTRYPOINT ["/bin/sh", "-c", "exec \"$SERVICE\" \"$@\"", "--"]

FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends git curl && apt-get clean
WORKDIR /usr/src/app
COPY pyproject.toml ./
RUN uv sync
COPY app app
COPY plugins plugins
COPY main.py main.py

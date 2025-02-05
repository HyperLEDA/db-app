FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends git && apt-get clean
WORKDIR /usr/src/app
COPY pyproject.toml ./
RUN uv sync
COPY app app
COPY main.py main.py
CMD ["uv", "run", "main.py", "adminapi"]

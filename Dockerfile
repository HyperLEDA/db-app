FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /usr/src/app
COPY pyproject.toml ./
RUN uv sync --verbose
COPY . .
CMD ["uv", "run", "main.py", "runserver"]

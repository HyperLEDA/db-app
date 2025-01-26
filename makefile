PYTHON := python

.PHONY: docs

all: test

## General targets

recreate-venv:
	uv venv

install:
	uv init

adminapi:
	uv run main.py adminapi -c configs/dev/adminapi.yaml

dataapi:
	uv run main.py dataapi -c configs/dev/dataapi.yaml

importer:
	uv run main.py importer -c configs/dev/importer.yaml

runworker:
	rq worker default

start-db:
	docker-compose up -d

stop-db:
	docker-compose down

docs:
	uv run main.py generate-spec -o docs/gen/swagger.json
	uvx \
		--with 'mkdocs-material>=9.5.50' \
		--with 'mkdocs-section-index>=0.3.9' \
		--with 'neoteroi-mkdocs>=1.1.0' \
		mkdocs serve -a localhost:8080

deploy-docs:
	uv run main.py generate-spec -o docs/gen/swagger.json
	uvx \
		--with 'mkdocs-material>=9.5.50' \
		--with 'mkdocs-section-index>=0.3.9' \
		--with 'neoteroi-mkdocs>=1.1.0' \
		mkdocs gh-deploy

build-docs:
	uv run main.py generate-spec -o docs/gen/swagger.json
	uvx \
		--with 'mkdocs-material>=9.5.50' \
		--with 'mkdocs-section-index>=0.3.9' \
		--with 'neoteroi-mkdocs>=1.1.0' \
		mkdocs build

## Testing

check:
	uvx ruff format --config=pyproject.toml --check
	uvx ruff check --config=pyproject.toml

# pytest is used to run unittest test cases
test: check
	uv run pytest --config-file=pyproject.toml tests/env_test.py
	uv run pytest --config-file=pyproject.toml tests/unit

test-all: check
	uv run pytest --config-file=pyproject.toml tests

test-regression:
	uv run main.py regression-tests

mypy:
	uvx mypy app --config-file pyproject.toml
	uvx mypy tests --config-file pyproject.toml

coverage:
	uvx coverage run -m unittest discover -s tests -p "*_test.py" -v
	uvx coverage html

## Fix code

fix:
	uvx ruff format --config=pyproject.toml
	uvx ruff check --config=pyproject.toml --fix

fix-unsafe:
	uvx ruff check --config=pyproject.toml --unsafe-fixes --fix

## Deploy

GIT_VERSION = `git rev-parse --short master`

image-build:
	docker build . -t ghcr.io/hyperleda/hyperleda:$(GIT_VERSION)
	docker tag ghcr.io/hyperleda/hyperleda:$(GIT_VERSION) ghcr.io/hyperleda/hyperleda:latest

image-push:
	docker push ghcr.io/hyperleda/hyperleda:$(GIT_VERSION)
	docker push ghcr.io/hyperleda/hyperleda:latest

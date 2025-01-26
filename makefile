PYTHON := python

.PHONY: docs

all: test

## General targets

recreate-venv:
	uv venv

install:
	uv init

runserver:
	$(PYTHON) main.py runserver -c configs/dev/config.yaml

rundataapi:
	$(PYTHON) main.py dataapi -c configs/dev/dataapi.yaml

runworker:
	rq worker default

start-db:
	docker-compose up -d

stop-db:
	docker-compose down

docs:
	uv run main.py generate-spec -o docs/gen/swagger.json
	uvx \
		--with mkdocs-material>=9.5.50 \
		--with mkdocs-section-index>=0.3.9 \
		--with neoteroi-mkdocs>=1.1.0 \
		mkdocs serve -a localhost:8080

deploy-docs:
	uv run main.py generate-spec -o docs/gen/swagger.json
	uvx \
		--with mkdocs-material>=9.5.50 \
		--with mkdocs-section-index>=0.3.9 \
		--with neoteroi-mkdocs>=1.1.0 \
		mkdocs gh-deploy

build-docs:
	uv run main.py generate-spec -o docs/gen/swagger.json
	uvx \
		--with mkdocs-material>=9.5.50 \
		--with mkdocs-section-index>=0.3.9 \
		--with neoteroi-mkdocs>=1.1.0 \
		mkdocs build

## Testing

check:
	$(PYTHON) -m ruff format --config=pyproject.toml --check
	$(PYTHON) -m ruff check --config=pyproject.toml

# we use pytest to run unittest test cases
test: check
	$(PYTHON) -m pytest --config-file=pyproject.toml tests/env_test.py
	$(PYTHON) -m pytest --config-file=pyproject.toml tests/unit

test-all: check
	$(PYTHON) -m pytest --config-file=pyproject.toml tests

test-regression:
	$(PYTHON) main.py regression-tests

mypy:
	$(PYTHON) -m mypy app --config-file pyproject.toml
	$(PYTHON) -m mypy tests --config-file pyproject.toml

coverage:
	$(PYTHON) -m coverage run -m unittest discover -s tests -p "*_test.py" -v
	$(PYTHON) -m coverage html

## Fix code

fix:
	$(PYTHON) -m ruff format --config=pyproject.toml
	$(PYTHON) -m ruff check --config=pyproject.toml --fix

fix-unsafe:
	$(PYTHON) -m ruff check --config=pyproject.toml --unsafe-fixes --fix

## Deploy

GIT_VERSION = `git rev-parse --short master`

image-build:
	docker build . -t ghcr.io/hyperleda/hyperleda:$(GIT_VERSION)
	docker tag ghcr.io/hyperleda/hyperleda:$(GIT_VERSION) ghcr.io/hyperleda/hyperleda:latest

image-push:
	docker push ghcr.io/hyperleda/hyperleda:$(GIT_VERSION)
	docker push ghcr.io/hyperleda/hyperleda:latest

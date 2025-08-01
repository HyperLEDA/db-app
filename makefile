PYTHON := python

.PHONY: docs

all: test

## General targets

install:
	uv sync

install-dev:
	uv sync --all-extras

adminapi:
	uv run main.py adminapi -c configs/dev/adminapi.yaml

adminapi-dev:
	set -a && source .env.local && set +a && make adminapi

dataapi:
	uv run main.py dataapi -c configs/dev/dataapi.yaml

default-rules:
	PGPASSWORD=password psql -h localhost -p 6432 --dbname hyperleda -U hyperleda -c "\copy layer0.homogenization_rules (catalog,parameter,key,filters,priority) FROM 'tests/assets/default_rules.csv' WITH ( FORMAT csv, HEADER true, QUOTE '\"', DELIMITER ',');"

start-db:
	docker-compose up -d

stop-db:
	docker-compose down

restart-db:
	make stop-db
	make start-db

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
	uv run tests.py regression-tests

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

deploy-test:
	uv run infra/deploy.py infra/settings/test.yaml

deploy-prod:
	uv run infra/deploy.py infra/settings/prod.yaml

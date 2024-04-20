PYTHON := python

.PHONY: docs

all: test

## General targets
install:
	$(PYTHON) -m pip install -r requirements.txt

runserver:
	$(PYTHON) main.py runserver -c configs/dev/config.yaml

runworker:
	rq worker default

start-db:
	docker compose up -d

stop-db:
	docker compose down

docs:
	$(PYTHON) -m mkdocs serve

deploy-docs:
	$(PYTHON) -m mkdocs gh-deploy

build-docs:
	$(PYTHON) -m mkdocs build

## Testing

test: check dryrun-isort test-unit

test-all: check dryrun-isort test-unit test-integration

test-extra: pylint mypy

check: check-format check-lint

check-format: dryrun-ruff-format

check-lint: dryrun-ruff-lint

dryrun-ruff-format:
	$(PYTHON) -m ruff format --config=pyproject.toml --check

dryrun-ruff-lint:
	$(PYTHON) -m ruff check --config=pyproject.toml

dryrun-isort:
	$(PYTHON) -m isort . --settings-path pyproject.toml --check-only

pylint:
	$(PYTHON) -m pylint . --recursive true --rcfile pyproject.toml

test-unit: # we use pytest to run unittest test cases
# first test that environment is installed correctly.
	$(PYTHON) -m pytest --config-file=pyproject.toml tests/env_test.py
# now run all the remaining tests
	$(PYTHON) -m pytest --config-file=pyproject.toml --ignore=tests/integration

test-integration:
	$(PYTHON) -m pytest --config-file=pyproject.toml tests/integration

mypy: mypy-app mypy-tests

mypy-app:
	$(PYTHON) -m mypy app --config-file pyproject.toml

mypy-tests:
	$(PYTHON) -m mypy tests --config-file pyproject.toml

coverage:
	$(PYTHON) -m coverage run -m unittest discover -s tests -p "*_test.py" -v
	$(PYTHON) -m coverage html

## Fix code

# alias
fix: fix-lint

fix-unsafe: lint-ruff-unsafe

fix-lint: format-ruff lint-ruff

format-ruff:
	$(PYTHON) -m ruff format --config=pyproject.toml

lint-ruff:
	$(PYTHON) -m ruff check --config=pyproject.toml --fix

lint-ruff-unsafe:
	$(PYTHON) -m ruff check --config=pyproject.toml --fix

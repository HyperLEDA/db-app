PYTHON := python

all: test

## General targets
install:
	$(PYTHON) -m pip install -r requirements.txt

runserver:
	$(PYTHON) main.py runserver -c configs/dev/config.yaml

start-db:
	docker compose up -d

stop-db:
	docker compose down

## Testing

test: dryrun-black dryrun-isort test-unit

test-all: dryrun-black dryrun-isort test-unit test-integration

test-extra: pylint mypy

dryrun-black:
	$(PYTHON) -m black . --config pyproject.toml --check

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

## Linters

fix-lint: black isort

black:
	$(PYTHON) -m black . --config pyproject.toml

isort:
	$(PYTHON) -m isort . --settings-path pyproject.toml

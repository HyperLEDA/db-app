PYTHON := python

install:
	$(PYTHON) -m pip install -r requirements.txt

runserver:
	$(PYTHON) main.py runserver -c configs/dev/config.yaml

# starts database and applies migrations
start-db:
	docker compose up -d

stop-db:
	docker compose down

test-all: check test

test:
	$(PYTHON) -m unittest discover -s tests -p "*_test.py" -v


fix-lint: black isort

black:
	$(PYTHON) -m black . --config pyproject.toml

isort:
	$(PYTHON) -m isort . --settings-path pyproject.toml


check: dryrun-black dryrun-isort

dryrun-black:
	$(PYTHON) -m black . --config pyproject.toml --check

dryrun-isort:
	$(PYTHON) -m isort . --settings-path pyproject.toml --check-only

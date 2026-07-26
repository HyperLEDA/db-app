install:
	uv sync

install-dev:
	uv sync --all-extras

MIGRATIONS_DIR = postgres/migrations

check-migrations:
	@invalid=$$( \
		ls $(MIGRATIONS_DIR) \
		| grep -vE '^V[0-9]{3}__[a-z0-9_]+\.sql$$' \
		|| true \
	); \
	dups=$$( \
		ls $(MIGRATIONS_DIR) \
		| sed -n 's/^V\([0-9]\{3\}\)__.*/\1/p' \
		| sort \
		| uniq -d \
	); \
	if [ -n "$$invalid" ]; then \
		echo "Invalid migration names:"; \
		echo "$$invalid"; \
		exit 1; \
	fi; \
	if [ -n "$$dups" ]; then \
		echo "Duplicate migration versions:"; \
		echo "$$dups"; \
		exit 1; \
	fi; \

check-schema:
	docker compose stop hyperledadb migrate wait-for-migrate
	docker compose rm -f -v hyperledadb migrate wait-for-migrate
	docker compose up -d hyperledadb migrate wait-for-migrate
	npx --yes schemalint@2.3.2

check:
	@output=$$(copier check-update --answers-file .template.yaml 2>&1) || true; \
	if echo "$$output" | grep -q "up-to-date"; then \
		true; \
	elif echo "$$output" | grep -q "New template version"; then \
		echo "Template update available, run make update-template"; \
	else \
		echo "$$output"; \
	fi

	@find . \
		-name "*.py" \
		-not -path "./.venv/*" \
		-not -path "./.git/*" \
		-exec uv run python -m py_compile {} +
	@echo "Compilation ok."

	@uv run ruff format \
		--quiet \
		--config=pyproject.toml \
		--check
	@echo "Formatting ok."

	@uv run ruff check \
		--quiet \
		--config=pyproject.toml
	@echo "Linter ok."

	@output=$$(uv run lint-imports 2>&1); exit_code=$$?; \
	if [ $$exit_code -ne 0 ]; then echo "$$output"; fi; \
	exit $$exit_code
	@echo "Import contracts ok."

	@output=$$(uv run basedpyright 2>&1); exit_code=$$?; \
	if [ $$exit_code -ne 0 ]; then echo "$$output"; fi; \
	exit $$exit_code
	@echo "Typechecking ok."

	@$(MAKE) check-migrations
	@echo "Migrations ok."

	@uv run pytest \
		--quiet \
		--config-file=pyproject.toml \
		tests/env_test.py tests/unit
	@echo "Testing ok."

fix:
	@uv run ruff format \
		--quiet \
		--config=pyproject.toml

	@uv run ruff check \
		--quiet \
		--config=pyproject.toml \
		--fix

check-deadcode:
	@uvx vulture

wheel:
	uv build --wheel

# only for mac as this is faster
build:
	docker build . \
		--platform linux/arm64

new-branch:
	@read -p "Branch name: " branch_name && \
	branch_name=$${branch_name// /-} && \
	base=$$(git remote show origin | sed -n '/HEAD branch/s/.*: //p') && \
	echo "Selecting $$base branch as default" && \
	git fetch origin $$base && \
	git checkout -b $$branch_name origin/$$base && \
	git push -u origin $$branch_name

update-template:
	copier update \
		--skip-answered \
		--conflict inline \
		--answers-file .template.yaml

## General targets

adminapi:
	uv run adminapi -c configs/dev/adminapi.yaml

adminapi-dev:
	set -a && source .env.local && set +a && make adminapi

dataapi:
	uv run dataapi -c configs/dev/dataapi.yaml

start-db:
	docker-compose up -d

stop-db:
	docker-compose down

restart-db:
	make stop-db
	make start-db

start-prefect:
	uv run prefect server start

start-tasks:
	uv run tasks

docs:
	uvx \
		--with 'mkdocs-material>=9.5.50' \
		--with 'mkdocs-section-index>=0.3.9' \
		mkdocs serve -a localhost:8080

deploy-docs:
	uvx \
		--with 'mkdocs-material>=9.5.50' \
		--with 'mkdocs-section-index>=0.3.9' \
		mkdocs gh-deploy

build-docs:
	uvx \
		--with 'mkdocs-material>=9.5.50' \
		--with 'mkdocs-section-index>=0.3.9' \
		mkdocs build

cleanup:
	rm -rf .venv .pytest_cache .ruff_cache \
		__pycache__ */__pycache__ \
		.coverage htmlcov site

## Testing

# pytest is used to run unittest test cases
test-all: check
	@uv run pytest \
		--config-file=pyproject.toml \
		--quiet \
		tests

test-regression:
	uv run tests.py regression-tests

coverage:
	uvx coverage run -m unittest discover -s tests -p "*_test.py" -v
	uvx coverage html

## Release

GIT_VERSION = `git rev-parse --short master`

image-build:
	docker build . -t ghcr.io/hyperleda/hyperleda:$(GIT_VERSION)
	docker tag ghcr.io/hyperleda/hyperleda:$(GIT_VERSION) ghcr.io/hyperleda/hyperleda:latest

image-push:
	docker push ghcr.io/hyperleda/hyperleda:$(GIT_VERSION)
	docker push ghcr.io/hyperleda/hyperleda:latest

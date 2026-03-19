install:
	uv sync

install-dev:
	uv sync --all-extras

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

	@uvx ruff format \
		--quiet \
		--config=pyproject.toml \
		--check

	@uvx ruff check \
		--quiet \
		--config=pyproject.toml

	@output=$$(uvx basedpyright 2>&1); exit_code=$$?; \
	if [ $$exit_code -ne 0 ]; then echo "$$output"; fi; \
	exit $$exit_code

	@uv run pytest \
		--quiet \
		--config-file=pyproject.toml \
		tests/env_test.py tests/unit

fix:
	@uvx ruff format \
		--quiet \
		--config=pyproject.toml

	@uvx ruff check \
		--quiet \
		--config=pyproject.toml \
		--fix

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
	uv run main.py adminapi -c configs/dev/adminapi.yaml

adminapi-dev:
	set -a && source .env.local && set +a && make adminapi

dataapi:
	uv run main.py dataapi -c configs/dev/dataapi.yaml

generate-spec:
	uv run main.py generate-spec -o res.json

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

cleanup:
	rm -rf uv.lock .venv \
		.pytest_cache .mypy_cache .vizier_cache .ruff_cache \
		__pycache__ */__pycache__ \
		.coverage htmlcov site \
		docs/gen

## Testing

# pytest is used to run unittest test cases
test-all: check
	@uv run pytest \
		--config-file=pyproject.toml \
		--quiet \
		tests

test-regression:
	uv run tests.py regression-tests

mypy:
	uvx mypy app --config-file pyproject.toml
	uvx mypy tests --config-file pyproject.toml

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

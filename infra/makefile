deploy:
	set -a && . .env.local && set +a && uv run scripts.py deploy

restart:
	set -a && . .env.local && set +a && ./scripts/restart.sh

deploy-test-db:
	set -a && . .env.local && set +a && ./scripts/deploy-test-db.sh

ssh $HOST "cd ~/hyperleda \
    && set -a \
    && . .env.local \
    && set +a \
    && docker compose stop \
    && docker compose up -d"

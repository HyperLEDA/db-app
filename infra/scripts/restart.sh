HOST=$HOST
BACKEND_USER=$BACKEND_USER

ssh $BACKEND_USER@$HOST "cd ~/hyperleda \
    && set -a \
    && . .env.local \
    && set +a \
    && docker compose stop \
    && docker compose rm -f \
    && docker compose pull \
    && docker compose up -d"

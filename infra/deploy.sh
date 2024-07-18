HOST=$HOST

scp docker-compose.yaml $HOST:~/hyperleda/docker-compose.yaml
ssh $HOST "rm -rf ~/hyperleda/configs"
scp -r configs/ $HOST:~/hyperleda/configs
scp -r ../configs/ $HOST:~/hyperleda
scp .env.remote $HOST:~/hyperleda/.env.local

ssh $HOST "cd ~/hyperleda && set -a && . .env.local && set +a && docker compose up -d"

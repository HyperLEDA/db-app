HOST=$HOST
BACKEND_USER=$BACKEND_USER

ssh $BACKEND_USER@$HOST "rm -rf ~/hyperleda/dev && mkdir ~/hyperleda/dev"
scp ../docker-compose.yaml $BACKEND_USER@$HOST:~/hyperleda/dev/docker-compose.yaml
scp -r ../postgres $BACKEND_USER@$HOST:~/hyperleda/dev

ssh $BACKEND_USER@$HOST "cd ~/hyperleda/dev && docker compose up -d"

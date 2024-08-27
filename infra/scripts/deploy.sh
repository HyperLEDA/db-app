HOST=$HOST
BACKEND_USER=$BACKEND_USER

cd ../../
scp infra/docker-compose.yaml $BACKEND_USER@$HOST:~/hyperleda/docker-compose.yaml
ssh $BACKEND_USER@$HOST "rm -rf ~/hyperleda/configs"
scp -r infra/configs/ $BACKEND_USER@$HOST:~/hyperleda/configs
scp -r configs/ $BACKEND_USER@$HOST:~/hyperleda
scp infra/.env.remote $BACKEND_USER@$HOST:~/hyperleda/.env.local
echo `git rev-parse --short HEAD` | ssh $BACKEND_USER@$HOST -T "cat > ~/hyperleda/version.txt"

HOST=$HOST

cd ../../
scp infra/docker-compose.yaml $HOST:~/hyperleda/docker-compose.yaml
ssh $HOST "rm -rf ~/hyperleda/configs"
scp -r infra/configs/ $HOST:~/hyperleda/configs
scp -r configs/ $HOST:~/hyperleda
scp infra/.env.remote $HOST:~/hyperleda/.env.local
echo `git rev-parse --short master` | ssh $HOST -T "cat > ~/hyperleda/version.txt"

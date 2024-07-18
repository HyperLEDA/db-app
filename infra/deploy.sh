HOST=$HOST

scp docker-compose.yaml $HOST:~/hyperleda/docker-compose.yaml
ssh $HOST "rm -rf ~/hyperleda/configs"
scp -r configs/ $HOST:~/hyperleda/configs
scp -r ../configs/ $HOST:~/hyperleda

ssh $HOST "cd ~/hyperleda && docker compose up -d"

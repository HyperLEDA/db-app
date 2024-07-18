HOST=$HOST

ssh $HOST "rm -rf ~/hyperleda/dev && mkdir ~/hyperleda/dev"
scp ../docker-compose.yaml $HOST:~/hyperleda/dev/docker-compose.yaml
scp -r ../postgres $HOST:~/hyperleda/dev

ssh $HOST "cd ~/hyperleda/dev && docker compose up -d"

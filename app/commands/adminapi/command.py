from typing import final

import structlog

from app.commands.adminapi import config
from app.commands.adminapi.depot import depot
from app.data import repositories
from app.lib import auth, clients, commands
from app.lib.storage import postgres, redis
from app.lib.web import server
from app.presentation import adminapi

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@final
class AdminAPICommand(commands.Command):
    def __init__(self, config_path: str):
        self.config_path = config_path

    def prepare(self):
        self.config = config.parse_config(self.config_path)

        self.pg_storage = postgres.PgStorage(self.config.storage, log)
        self.pg_storage.connect()

        self.redis_storage = redis.RedisQueue(self.config.queue, log)
        self.redis_storage.connect()

        d = depot.Depot(
            common_repo=repositories.CommonRepository(self.pg_storage, log),
            layer0_repo=repositories.Layer0Repository(self.pg_storage, log),
            layer1_repo=repositories.Layer1Repository(self.pg_storage, log),
            layer2_repo=repositories.Layer2Repository(self.pg_storage, log),
            tmp_data_repo=repositories.TmpDataRepositoryImpl(self.pg_storage),
            queue_repo=repositories.QueueRepository(self.redis_storage, self.config.storage, log),
            authenticator=auth.PostgresAuthenticator(self.pg_storage),
            clients=clients.Clients(self.config.clients.ads_token),
        )

        routes = []

        for handler in adminapi.routes:
            routes.append(handler(d))

        middlewares = []
        if self.config.auth_enabled:
            middlewares.append(server.get_auth_middleware("/api/v1/admin", d.authenticator))

        self.app = server.WebServer(routes, self.config.server, middlewares=middlewares)

    def run(self):
        self.app.run()

    def cleanup(self):
        self.redis_storage.disconnect()
        self.pg_storage.disconnect()

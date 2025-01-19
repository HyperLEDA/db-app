import structlog

from app import commands as appcommands
from app.commands.runserver import config
from app.data import repositories
from app.lib import auth, clients, commands
from app.lib.server import middleware, server
from app.lib.storage import postgres, redis
from app.presentation.server import handlers

log: structlog.stdlib.BoundLogger = structlog.get_logger()


class RunServerCommand(commands.Command):
    def __init__(self, config_path: str):
        self.config_path = config_path

    def prepare(self):
        self.cfg = config.parse_config(self.config_path)

        self.pg_storage = postgres.PgStorage(self.cfg.storage, log)
        self.pg_storage.connect()

        self.redis_storage = redis.RedisQueue(self.cfg.queue, log)
        self.redis_storage.connect()

        depot = appcommands.Depot(
            common_repo=repositories.CommonRepository(self.pg_storage, log),
            layer0_repo=repositories.Layer0Repository(self.pg_storage, log),
            layer1_repo=repositories.Layer1Repository(self.pg_storage, log),
            layer2_repo=repositories.Layer2Repository(self.pg_storage, log),
            tmp_data_repo=repositories.TmpDataRepositoryImpl(self.pg_storage),
            queue_repo=repositories.QueueRepository(self.redis_storage, self.cfg.storage, log),
            authenticator=auth.PostgresAuthenticator(self.pg_storage),
            clients=clients.Clients(self.cfg.clients.ads_token),
        )

        routes = []

        for handler in handlers.routes:
            routes.append(handler(depot))

        middlewares = []
        if self.cfg.auth_enabled:
            middlewares.append(middleware.get_auth_middleware("/api/v1/admin", depot.authenticator))

        self.app = server.WebServer(routes, middlewares=middlewares)

    def run(self):
        self.app.run(self.cfg.server)

    def cleanup(self):
        self.redis_storage.disconnect()
        self.pg_storage.disconnect()

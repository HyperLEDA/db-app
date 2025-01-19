import structlog

from app import commands as appcommands
from app.commands.runserver import config
from app.data import repositories
from app.lib import auth, clients, commands
from app.lib.storage import postgres, redis
from app.presentation import server
from app.presentation.server import handlers


class RunServerCommand(commands.Command):
    def __init__(self, config_path: str):
        self.config_path = config_path

    def prepare(self):
        self.cfg = config.parse_config(self.config_path)

        self.logger: structlog.stdlib.BoundLogger = structlog.get_logger()

        self.pg_storage = postgres.PgStorage(self.cfg.storage, self.logger)
        self.pg_storage.connect()

        self.redis_storage = redis.RedisQueue(self.cfg.queue, self.logger)
        self.redis_storage.connect()

        self.depot = appcommands.Depot(
            common_repo=repositories.CommonRepository(self.pg_storage, self.logger),
            layer0_repo=repositories.Layer0Repository(self.pg_storage, self.logger),
            layer1_repo=repositories.Layer1Repository(self.pg_storage, self.logger),
            layer2_repo=repositories.Layer2Repository(self.pg_storage, self.logger),
            tmp_data_repo=repositories.TmpDataRepositoryImpl(self.pg_storage),
            queue_repo=repositories.QueueRepository(self.redis_storage, self.cfg.storage, self.logger),
            authenticator=auth.PostgresAuthenticator(self.pg_storage),
            clients=clients.Clients(self.cfg.clients.ads_token),
        )

    def run(self):
        routes = []

        for handler in handlers.routes:
            routes.append(handler(self.depot))

        app = server.init_app(self.cfg.server, self.depot.authenticator, routes)

        server.run_app(app, self.cfg.server)

    def cleanup(self):
        self.redis_storage.disconnect()
        self.pg_storage.disconnect()

from typing import final

import structlog

from app.commands.adminapi import config
from app.data import repositories
from app.domain import adminapi as domain
from app.lib import auth, clients, commands
from app.lib.storage import postgres, redis
from app.lib.web import server
from app.presentation import adminapi as presentation

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@final
class AdminAPICommand(commands.Command):
    """
    Starts the API server for the admin interface of the database.
    """

    def __init__(self, config_path: str):
        self.config_path = config_path

    def prepare(self):
        cfg = config.parse_config(self.config_path)

        self.pg_storage = postgres.PgStorage(cfg.storage, log)
        self.pg_storage.connect()

        self.redis_storage = redis.RedisQueue(cfg.queue, log)
        self.redis_storage.connect()

        authenticator = auth.PostgresAuthenticator(self.pg_storage)

        actions = domain.Actions(
            common_repo=repositories.CommonRepository(self.pg_storage, log),
            layer0_repo=repositories.Layer0Repository(self.pg_storage, log),
            layer1_repo=repositories.Layer1Repository(self.pg_storage, log),
            layer2_repo=repositories.Layer2Repository(self.pg_storage, log),
            queue_repo=repositories.QueueRepository(self.redis_storage, cfg.storage, log),
            authenticator=authenticator,
            clients=clients.Clients(cfg.clients.ads_token),
        )

        middlewares = []
        if cfg.auth_enabled:
            middlewares.append(server.get_auth_middleware("/api/v1/admin", authenticator))

        self.app = presentation.Server(actions, cfg.server, middlewares=middlewares)

    def run(self):
        self.app.run()

    def cleanup(self):
        self.redis_storage.disconnect()
        self.pg_storage.disconnect()

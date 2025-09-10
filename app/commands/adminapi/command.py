from pathlib import Path
from typing import final

import pydantic_settings as settings
import structlog
import yaml

from app.data import repositories
from app.domain import adminapi as domain
from app.lib import auth, clients, commands, config
from app.lib.storage import postgres, redis
from app.lib.web import middlewares, server
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
        cfg = parse_config(self.config_path)

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

        self.app = presentation.Server(actions, cfg.server, log)

        if cfg.auth_enabled:
            self.app.add_mw(middlewares.AuthMiddleware, authenticator)

    def run(self):
        self.app.run()

    def cleanup(self):
        if self.redis_storage:
            self.redis_storage.disconnect()
        if self.pg_storage:
            self.pg_storage.disconnect()


class ClientsConfig(config.ConfigSettings):
    model_config = settings.SettingsConfigDict(env_prefix="CLIENTS_")

    enabled: bool
    ads_token: str


class Config(config.ConfigSettings):
    server: server.ServerConfig
    storage: postgres.PgStorageConfig
    queue: redis.QueueConfig
    clients: ClientsConfig
    auth_enabled: bool


def parse_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())

    return Config(**data)

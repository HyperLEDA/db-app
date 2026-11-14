from pathlib import Path
from typing import final

import pydantic
import pydantic_settings as settings
import structlog
import yaml

from app.adminapi import clients, domain, presentation, repository
from app.lib import audit, auth, commands, config, tracing
from app.lib.storage import enums, postgres
from app.lib.tracing import TracingConfig
from app.lib.web import server

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@final
class AdminAPICommand(commands.Command):
    """
    Starts the API server for the admin interface of the database.
    """

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.pg_storage: postgres.PgStorage | None = None
        self.app: presentation.Server | None = None

    def prepare(self):
        cfg = parse_config(self.config_path)

        tracing.setup_tracing("adminapi", cfg.tracing)

        self.pg_storage = postgres.PgStorage(cfg.storage, log, enums.PG_ENUM_REGISTRY)
        self.pg_storage.connect()

        authenticator: auth.Authenticator = (
            auth.PostgresAuthenticator(self.pg_storage) if cfg.auth_enabled else auth.NoopAuthenticator()
        )
        action_recorder: audit.ActionRecorder = (
            audit.PostgresActionRecorder(self.pg_storage) if cfg.auth_enabled else audit.NoopActionRecorder()
        )

        repo = repository.Repository(self.pg_storage, log)

        actions = domain.Actions(
            repo=repo,
            authenticator=authenticator,
            storage=self.pg_storage,
            clients=clients.Clients(cfg.clients.ads_token, cfg.prefect.api_url),
        )

        self.app = presentation.Server(
            actions,
            cfg.server,
            log,
            authenticator,
            action_recorder,
            auth_enabled=cfg.auth_enabled,
        )

    def run(self):
        if self.app is None:
            raise RuntimeError("prepare() was not called")
        self.app.run()

    def cleanup(self):
        if self.pg_storage:
            self.pg_storage.disconnect()


class ClientsConfig(config.ConfigSettings):
    model_config = settings.SettingsConfigDict(env_prefix="CLIENTS_")

    ads_token: str


class PrefectConfig(config.ConfigSettings):
    model_config = settings.SettingsConfigDict(env_prefix="PREFECT_")

    api_url: str = "http://localhost:4200/api"


class Config(config.ConfigSettings):
    server: server.ServerConfig
    storage: postgres.PgStorageConfig
    clients: ClientsConfig
    prefect: PrefectConfig = pydantic.Field(default_factory=PrefectConfig)
    auth_enabled: bool = True
    tracing: TracingConfig = pydantic.Field(default_factory=TracingConfig)


def parse_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())

    return Config(**data)

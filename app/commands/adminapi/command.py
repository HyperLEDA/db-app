import threading
from datetime import timedelta
from pathlib import Path
from typing import final

import pydantic
import pydantic_settings as settings
import structlog
import yaml

from app.data import model, repositories
from app.domain import adminapi as domain
from app.domain.adminapi import CacheRegistry
from app.lib import auth, clients, commands, config, tracing
from app.lib.cache import BackgroundCache
from app.lib.storage import postgres
from app.lib.tracing import TracingConfig
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
        cfg = parse_config(self.config_path)

        tracing.setup_tracing("adminapi", cfg.tracing)

        self.pg_storage = postgres.PgStorage(cfg.storage, log)
        self.pg_storage.connect()

        authenticator: auth.Authenticator = (
            auth.PostgresAuthenticator(self.pg_storage) if cfg.auth_enabled else auth.NoopAuthenticator()
        )

        layer0_repo = repositories.Layer0Repository(self.pg_storage, log)

        def refresh_rawdata_row_counts() -> model.RawdataTableRowCounts:
            names = layer0_repo.list_tables()
            return model.RawdataTableRowCounts(rows_by_table={name: layer0_repo.total_rows(name) for name in names})

        rawdata_row_counts: BackgroundCache[model.RawdataTableRowCounts] = BackgroundCache(
            name="rawdata_table_row_counts",
            refresh_func=refresh_rawdata_row_counts,
            refresh_frequency=timedelta(minutes=1),
            refresh_timeout=timedelta(seconds=30),
        )
        cache_thread = threading.Thread(target=rawdata_row_counts.run, daemon=True)
        cache_thread.start()

        cache_registry = CacheRegistry(rawdata_row_counts=rawdata_row_counts)

        actions = domain.Actions(
            common_repo=repositories.CommonRepository(self.pg_storage, log),
            layer0_repo=layer0_repo,
            layer1_repo=repositories.Layer1Repository(self.pg_storage, log),
            layer2_repo=repositories.Layer2Repository(self.pg_storage, log),
            authenticator=authenticator,
            clients=clients.Clients(cfg.clients.ads_token),
            cache_registry=cache_registry,
        )

        self.app = presentation.Server(
            actions,
            cfg.server,
            log,
            authenticator,
            enforce_route_auth=cfg.auth_enabled,
        )

    def run(self):
        self.app.run()

    def cleanup(self):
        if self.pg_storage:
            self.pg_storage.disconnect()


class ClientsConfig(config.ConfigSettings):
    model_config = settings.SettingsConfigDict(env_prefix="CLIENTS_")

    ads_token: str


class Config(config.ConfigSettings):
    server: server.ServerConfig
    storage: postgres.PgStorageConfig
    clients: ClientsConfig
    auth_enabled: bool = True
    tracing: TracingConfig = pydantic.Field(
        default_factory=lambda: TracingConfig(endpoint="localhost:4317", enabled=False)
    )


def parse_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())

    return Config(**data)

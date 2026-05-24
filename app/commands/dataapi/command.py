from pathlib import Path
from typing import Any, final

import pydantic
import pydantic_settings as settings
import structlog
import yaml

from app.data import repositories
from app.domain import dataapi as domain
from app.domain import responders
from app.lib import auth, commands, config, tracing
from app.lib.storage import postgres
from app.lib.tracing import TracingConfig
from app.lib.web import server
from app.presentation import dataapi as presentation

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@final
class DataAPICommand(commands.Command):
    """
    Starts the API server for the data interface of the database. This interface is
    used to obtain the data stored in aggregated catalogs.
    """

    def __init__(self, config_path: str) -> None:
        self.config_path = config_path

    def prepare(self):
        self.config = parse_config(self.config_path)

        tracing.setup_tracing("dataapi", self.config.tracing)

        self.pg_auth = postgres.PgStorage(self.config.storage.auth, log)
        self.pg_main = postgres.PgStorage(self.config.storage.main, log)

        authenticator: auth.Authenticator = (
            auth.PostgresAuthenticator(self.pg_auth) if self.config.auth_enabled else auth.NoopAuthenticator()
        )

        self.pg_auth.connect()
        self.pg_main.connect()

        actions = domain.Actions(
            layer2_repo=repositories.Layer2Repository(self.pg_main, log),
            catalog_cfg=self.config.catalogs,
            metadata_repo=repositories.MetadataRepository(self.pg_main),
        )

        self.app = presentation.Server(
            actions,
            self.config.server,
            log,
            authenticator,
            enforce_route_auth=self.config.auth_enabled,
        )

    def run(self):
        self.app.run()

    def cleanup(self):
        if self.pg_auth:
            self.pg_auth.disconnect()
        if self.pg_main:
            self.pg_main.disconnect()


class StorageConfig(pydantic.BaseModel):
    auth: postgres.PgStorageConfig
    main: postgres.PgStorageConfig


class Config(config.ConfigSettings):
    server: server.ServerConfig
    storage: StorageConfig
    catalogs: responders.CatalogConfig
    auth_enabled: bool = True
    tracing: TracingConfig = pydantic.Field(
        default_factory=lambda: TracingConfig(endpoint="localhost:4317", enabled=False)
    )


def _load_named_storage(name: str, data: dict[str, Any]) -> postgres.PgStorageConfig:
    class _Cfg(postgres.PgStorageConfig):
        model_config = settings.SettingsConfigDict(env_prefix=f"STORAGE_{name.upper()}_")

    return _Cfg(**data)


def parse_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())
    raw_storage = data.get("storage", {}) or {}
    data["storage"] = StorageConfig(
        auth=_load_named_storage("auth", raw_storage.get("auth", {})),
        main=_load_named_storage("main", raw_storage.get("main", {})),
    )

    return Config(**data)

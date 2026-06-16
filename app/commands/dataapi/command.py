import threading
from datetime import timedelta
from pathlib import Path
from typing import Any, final

import pydantic
import pydantic_settings as settings
import structlog
import yaml

from app.data import repositories
from app.domain import dataapi as domain
from app.domain import responders
from app.domain.designation import DesignationFormatter
from app.lib import auth, cache, commands, config, tracing
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
        self.pg_auth: postgres.PgStorage | None = None
        self.pg_main: postgres.PgStorage | None = None
        self.designation_rules_cache: cache.BackgroundCache | None = None
        self._designation_rules_thread: threading.Thread | None = None
        self.app: presentation.Server | None = None

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

        designation_rules_repo = repositories.DesignationRulesRepository(self.pg_main, log)
        self.designation_rules_cache = cache.BackgroundCache(
            "designation_rules",
            designation_rules_repo.snapshot,
            refresh_frequency=timedelta(seconds=30),
            refresh_timeout=timedelta(seconds=10),
        )
        self._designation_rules_thread = threading.Thread(
            target=self.designation_rules_cache.run,
            daemon=True,
        )
        self._designation_rules_thread.start()

        designation_formatter = DesignationFormatter(self.designation_rules_cache.get)

        actions = domain.Actions(
            layer2_repo=repositories.Layer2Repository(self.pg_main, log),
            catalog_cfg=self.config.catalogs,
            metadata_repo=repositories.MetadataRepository(self.pg_main),
            designation_formatter=designation_formatter,
        )

        self.app = presentation.Server(
            actions,
            self.config.server,
            log,
            authenticator,
            auth_enabled=self.config.auth_enabled,
        )

    def run(self):
        if self.app is None:
            raise RuntimeError("prepare() was not called")
        self.app.run()

    def cleanup(self):
        if self.designation_rules_cache is not None:
            self.designation_rules_cache.stop()
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

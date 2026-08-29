from pathlib import Path
from typing import final

import pydantic
import structlog
import yaml

from app.data import enums as data_enums
from app.data import repositories
from app.dataapi import clients, domain, presentation, responders
from app.dataapi.repository import Repository
from app.lib import commands, config, tracing
from app.lib.storage import postgres
from app.lib.tracing import TracingConfig
from app.lib.web import server

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@final
class DataAPICommand(commands.Command):
    """
    Starts the API server for the data interface of the database. This interface is
    used to obtain the data stored in aggregated catalogs.
    """

    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        self.pg_storage: postgres.PgStorage | None = None
        self.app: presentation.Server | None = None

    def prepare(self):
        self.config = parse_config(self.config_path)

        tracing.setup_tracing("dataapi", self.config.tracing)

        self.pg_storage = postgres.PgStorage(self.config.storage, log, data_enums.PG_ENUM_REGISTRY)
        self.pg_storage.connect()

        actions = domain.Actions(
            layer2_repo=repositories.Layer2Repository(self.pg_storage, log),
            repo=Repository(self.pg_storage),
            catalog_cfg=self.config.catalogs,
            metadata_repo=repositories.MetadataRepository(self.pg_storage),
            references_repo=repositories.ReferencesRepository(self.pg_storage),
            fieldapi_client=clients.RequestsFieldAPIClient(
                self.config.fieldapi.base_url,
                timeout_seconds=self.config.fieldapi.timeout_seconds,
            ),
        )

        self.app = presentation.Server(actions, self.config.server, log)

    def run(self):
        if self.app is None:
            raise RuntimeError("prepare() was not called")
        self.app.run()

    def cleanup(self):
        if self.pg_storage:
            self.pg_storage.disconnect()


class FieldAPIConfig(pydantic.BaseModel):
    base_url: str
    timeout_seconds: float = 10.0


class Config(config.ConfigSettings):
    server: server.ServerConfig
    storage: postgres.PgStorageConfig
    catalogs: responders.CatalogConfig
    fieldapi: FieldAPIConfig
    tracing: TracingConfig = pydantic.Field(
        default_factory=lambda: TracingConfig(endpoint="localhost:4317", enabled=False)
    )


def parse_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())
    return Config(**data)

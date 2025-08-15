from pathlib import Path
from typing import final

import structlog
import yaml

from app.data import repositories
from app.domain import dataapi as domain
from app.domain import responders
from app.lib import commands, config
from app.lib.storage import postgres
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

        self.pg_storage = postgres.PgStorage(self.config.storage, log)
        self.pg_storage.connect()

        actions = domain.Actions(
            layer2_repo=repositories.Layer2Repository(self.pg_storage, log),
            catalog_cfg=self.config.catalogs,
        )

        self.app = presentation.Server(actions, self.config.server, log)

    def run(self):
        self.app.run()

    def cleanup(self):
        self.pg_storage.disconnect()


class Config(config.ConfigSettings):
    server: server.ServerConfig
    storage: postgres.PgStorageConfig
    catalogs: responders.CatalogConfig


def parse_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())

    return Config(**data)

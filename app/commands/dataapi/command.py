from typing import final

import structlog

from app.commands.dataapi import config
from app.data import repositories
from app.domain import dataapi as domain
from app.lib import commands
from app.lib.storage import postgres
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
        self.config = config.parse_config(self.config_path)

        self.pg_storage = postgres.PgStorage(self.config.storage, log)
        self.pg_storage.connect()

        actions = domain.Actions(
            layer2_repo=repositories.Layer2Repository(self.pg_storage, log),
        )

        self.app = presentation.Server(actions, self.config.server, log)

    def run(self):
        self.app.run()

    def cleanup(self):
        self.pg_storage.disconnect()

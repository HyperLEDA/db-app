from typing import final

import structlog

from app.commands.importer import config
from app.lib import commands
from app.lib.storage import postgres

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@final
class ImporterCommand(commands.Command):
    def __init__(self, config_path: str) -> None:
        self.config_path = config_path

    def prepare(self):
        self.config = config.parse_config(self.config_path)

        self.pg_storage = postgres.PgStorage(self.config.storage, log)
        self.pg_storage.connect()

    def run(self):
        # 1. for each catalog on layer 1 collect all objects that were modified
        # since the last import: collect(dt) -> dict[pgc, UnaggregatedInfo]
        # 2. for each pgc aggregate all objects: aggregate(pgc, dict[pgc, UnaggregatedInfo]) -> ObjectInfo
        # 3. write objects to the storage: write(objects: dict[pgc, ObjectInfo]) -> None

        raise NotImplementedError

    def cleanup(self):
        self.pg_storage.disconnect()

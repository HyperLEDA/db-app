from typing import final

import structlog

from app.commands.importer import config
from app.data import repositories
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

        self.layer1_repository = repositories.Layer1Repository(self.pg_storage, log)
        self.layer2_repository = repositories.Layer2Repository(self.pg_storage, log)

    def run(self):
        # 1. for each catalog on layer 1 collect all objects that were modified
        # since the last import: collect(dt) -> dict[pgc, UnaggregatedInfo]
        # 2. for each pgc aggregate all objects: aggregate(pgc, dict[pgc, UnaggregatedInfo]) -> ObjectInfo
        # 3. write objects to the storage: write(objects: dict[pgc, ObjectInfo]) -> None

        # last_update_dt = self.layer2_repository.get_last_update_time()
        # new_objects = self.layer1_repository.get_new_objects(last_update_dt)

        raise NotImplementedError

    def cleanup(self):
        self.pg_storage.disconnect()

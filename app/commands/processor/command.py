from typing import final

import structlog

from app.commands.processor import config
from app.data import repositories
from app.lib.commands import interface
from app.lib.storage import postgres

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@final
class ProcessorCommand(interface.Command):
    """
    Command that performs processing on the input table.
    Processing includes cross-identification of the objects from the input table with the
    objects on layer 2 of the database.
    """

    def __init__(self, config_path: str, table_id: int) -> None:
        self.config_path = config_path
        self.table_id = table_id

    def prepare(self):
        self.config = config.parse_config(self.config_path)

        self.pg_storage = postgres.PgStorage(self.config.storage, log)
        self.pg_storage.connect()

        self.layer0_repository = repositories.Layer0Repository(self.pg_storage, log)
        self.layer2_repository = repositories.Layer2Repository(self.pg_storage, log)

    def run(self):
        log.info("starting processing", table_id=self.table_id)

    def cleanup(self):
        self.pg_storage.disconnect()

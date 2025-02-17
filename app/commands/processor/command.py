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

    def __init__(self, config_path: str, table_id: int, batch_size: int) -> None:
        self.config_path = config_path
        self.table_id = table_id
        self.batch_size = batch_size

    def prepare(self):
        self.config = config.parse_config(self.config_path)

        self.pg_storage = postgres.PgStorage(self.config.storage, log)
        self.pg_storage.connect()

        self.layer0_repo = repositories.Layer0Repository(self.pg_storage, log)
        self.layer2_repo = repositories.Layer2Repository(self.pg_storage, log)

    def run(self):
        data = self.layer0_repo.fetch_raw_data(
            self.table_id, order_column=repositories.INTERNAL_ID_COLUMN_NAME, limit=r.batch_size, offset=offset
        )



    def cleanup(self):
        self.pg_storage.disconnect()

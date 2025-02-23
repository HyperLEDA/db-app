from typing import final

import structlog

from app.commands.layer1_importer import config
from app.data import model, repositories
from app.lib import commands, containers
from app.lib.storage import postgres

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@final
class Layer1ImporterCommand(commands.Command):
    """
    Imports objects from layer 0 to layer 1.
    Only the objects that have `new` or `existing` status are imported.
    For `existing` objects, the PGC is taken from the metadata.
    """

    def __init__(self, config_path: str, table_id: int, batch_size: int) -> None:
        self.config_path = config_path
        self.table_id = table_id
        self.batch_size = batch_size

    def prepare(self):
        self.config = config.parse_config(self.config_path)

        self.pg_storage = postgres.PgStorage(self.config.storage, log)
        self.pg_storage.connect()

        self.common_repository = repositories.CommonRepository(self.pg_storage, log)
        self.layer0_repository = repositories.Layer0Repository(self.pg_storage, log)
        self.layer1_repository = repositories.Layer1Repository(self.pg_storage, log)

    def run(self):
        ctx = {"table_id": self.table_id}
        log.info("Starting import of objects", **ctx)

        for offset, data in containers.read_batches(
            self.layer0_repository.get_processed_objects,
            lambda data: len(data) == 0,
            self.table_id,
        ):
            new_objects_num = 0
            for obj in data:
                if isinstance(obj.processing_result, model.CIResultObjectNew):
                    new_objects_num += 1

            pgc_list: list[int] = []

            with self.common_repository.with_tx():
                if new_objects_num > 0:
                    pgc_list = self.common_repository.generate_pgc(new_objects_num)

                layer1_objects = []

                for obj in data:
                    pgc = None
                    if isinstance(obj.processing_result, model.CIResultObjectNew):
                        pgc = pgc_list.pop()
                    elif isinstance(obj.processing_result, model.CIResultObjectExisting):
                        pgc = obj.processing_result.pgc
                    else:
                        continue

                    for catalog_obj in obj.data:
                        layer1_objects.append(model.Layer1CatalogObject(pgc, obj.object_id, catalog_obj))

                self.layer1_repository.save_data(layer1_objects)

            log.info("Processed batch", done=offset, **ctx)

    def cleanup(self):
        self.pg_storage.disconnect()

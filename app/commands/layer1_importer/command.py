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
            with self.layer0_repository.with_tx():
                pgcs: dict[str, int | None] = {}

                for obj in data:
                    if isinstance(obj.processing_result, model.CIResultObjectNew):
                        pgcs[obj.object_id] = None
                    elif isinstance(obj.processing_result, model.CIResultObjectExisting):
                        pgcs[obj.object_id] = obj.processing_result.pgc
                    else:
                        continue

                self.layer0_repository.upsert_pgc(pgcs)

                layer1_objects = []

                for obj in data:
                    if obj.object_id not in pgcs:
                        continue

                    for catalog_obj in obj.data:
                        layer1_objects.append(model.Layer1Observation(obj.object_id, catalog_obj))

                self.layer1_repository.save_data(layer1_objects)

            log.info("Processed batch", done=offset, **ctx)

    def cleanup(self):
        self.pg_storage.disconnect()

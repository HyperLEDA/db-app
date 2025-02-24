from typing import final

import structlog

from app.data import model, repositories
from app.lib import containers
from app.lib.storage import postgres
from app.tasks import interface


@final
class Layer1ImportTask(interface.Task):
    def __init__(self, table_id: int, batch_size: int) -> None:
        self.table_id = table_id
        self.batch_size = batch_size
        self.log = structlog.get_logger()

    @classmethod
    def name(cls) -> str:
        return "layer1-import"

    def prepare(self, config: interface.Config):
        self.pg_storage = postgres.PgStorage(config.storage, self.log)
        self.pg_storage.connect()

        self.layer0_repository = repositories.Layer0Repository(self.pg_storage, self.log)
        self.layer1_repository = repositories.Layer1Repository(self.pg_storage, self.log)

    def run(self):
        ctx = {"table_id": self.table_id}
        self.log.info("Starting import of objects", **ctx)

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

            self.log.info("Processed batch", done=offset, **ctx)

    def cleanup(self):
        self.pg_storage.disconnect()

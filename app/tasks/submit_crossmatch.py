import uuid
from typing import final

import structlog

from app.data import model, repositories
from app.lib import containers
from app.lib.storage import postgres
from app.tasks import interface


@final
class SubmitCrossmatchTask(interface.Task):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        table_name: str,
        batch_size: int,
    ) -> None:
        self.table_name = table_name
        self.batch_size = batch_size
        self.log = logger

    @classmethod
    def name(cls) -> str:
        return "submit-crossmatch"

    def prepare(self, config: interface.Config):
        self.pg_storage = postgres.PgStorage(config.storage, self.log)
        self.pg_storage.connect()

        self.layer0_repository = repositories.Layer0Repository(self.pg_storage, self.log)

    def run(self):
        ctx = {"table_name": self.table_name}

        for offset, data in containers.read_batches(
            self.layer0_repository.get_processed_objects,
            lambda data: len(data) == 0,
            "",
            lambda d, _: d[-1].object_id,
            table_name=self.table_name,
            batch_size=self.batch_size,
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

            last_uuid = uuid.UUID(offset or "00000000-0000-0000-0000-000000000000")
            max_uuid = uuid.UUID("FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF")

            self.log.info(
                "Processed batch",
                last_object=offset,
                updated=len(data),
                very_approximate_progress=f"{last_uuid.int / max_uuid.int * 100:.03f}%",
                **ctx,
            )

    def cleanup(self):
        self.pg_storage.disconnect()

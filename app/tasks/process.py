from typing import final

import structlog

from app.data import repositories
from app.domain import processing
from app.lib.storage import postgres
from app.tasks import interface


@final
class ProcessTask(interface.Task):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        table_id: int,
        batch_size: int = 500,
        workers: int = 8,
    ) -> None:
        self.table_id = table_id
        self.batch_size = batch_size
        self.workers = workers
        self.log = logger

    @classmethod
    def name(cls) -> str:
        return "process"

    def prepare(self, config: interface.Config):
        self.pg_storage = postgres.PgStorage(config.storage, self.log)
        self.pg_storage.connect()

        self.layer0_repo = repositories.Layer0Repository(self.pg_storage, self.log)
        self.layer2_repo = repositories.Layer2Repository(self.pg_storage, self.log)

    def run(self):
        ctx = {"table_id": self.table_id}
        self.log.info("Starting marking of objects", **ctx)
        processing.mark_objects(self.layer0_repo, self.table_id, self.batch_size)

    def cleanup(self):
        self.pg_storage.disconnect()

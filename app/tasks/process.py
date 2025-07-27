from concurrent import futures
from typing import final

import structlog

from app.data import model, repositories
from app.domain import processing
from app.lib import containers
from app.lib.storage import postgres
from app.tasks import interface


@final
class ProcessTask(interface.Task):
    def __init__(
        self, table_id: int, batch_size: int = 500, workers: int = 8, crossmatch_enabled: bool = False
    ) -> None:
        self.table_id = table_id
        self.batch_size = batch_size
        self.workers = workers
        self.log = structlog.get_logger()
        self.crossmatch_enabled = crossmatch_enabled

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

        if not self.crossmatch_enabled:
            return

        self.log.info("Erasing previous crossmatching results", **ctx)
        self.layer0_repo.erase_crossmatch_results(self.table_id)

        self.log.info("Starting cross-identification", **ctx)
        for offset, data in containers.read_batches(
            self.layer0_repo.get_objects_by_id,
            lambda data: len(data) == 0,
            0,
            lambda _, offset: offset + self.batch_size,
            self.table_id,
            batch_size=self.batch_size,
        ):
            crossmatch_results: dict[str, model.CIResult] = {}

            with futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
                chunk_size = len(data) // self.workers
                if chunk_size == 0:
                    chunk_size = len(data)

                data_chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

                future_results = [
                    executor.submit(processing.crossmatch, self.layer2_repo, chunk) for chunk in data_chunks
                ]

                for future in futures.as_completed(future_results):
                    crossmatch_results.update(future.result())

            self.layer0_repo.add_crossmatch_result(crossmatch_results)

            self.log.info("Processed batch", done=offset, **ctx)

    def cleanup(self):
        self.pg_storage.disconnect()

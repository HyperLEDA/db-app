from concurrent import futures
from typing import final

import structlog

from app.commands.processor import config
from app.data import model, repositories
from app.domain import processing
from app.lib import containers
from app.lib.commands import interface
from app.lib.storage import postgres

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@final
class ProcessorCommand(interface.Command):
    """
    Command that performs processing on the input table.
    Processing includes cross-identification of the objects from the input table with the
    objects on layer 2 of the database.

    TODO: add option to not overwrite previous results.
    """

    def __init__(self, config_path: str, table_id: int, batch_size: int, workers: int) -> None:
        self.config_path = config_path
        self.table_id = table_id
        self.batch_size = batch_size
        self.workers = workers

    def prepare(self):
        self.config = config.parse_config(self.config_path)

        self.pg_storage = postgres.PgStorage(self.config.storage, log)
        self.pg_storage.connect()

        self.layer0_repo = repositories.Layer0Repository(self.pg_storage, log)
        self.layer2_repo = repositories.Layer2Repository(self.pg_storage, log)

    def run(self):
        ctx = {"table_id": self.table_id}
        log.info("Starting marking of objects", **ctx)
        processing.mark_objects(self.layer0_repo, self.table_id, self.batch_size)

        log.info("Erasing previous crossmatching results", **ctx)
        self.layer0_repo.erase_crossmatch_results(self.table_id)

        log.info("Starting cross-identification", **ctx)
        for offset, data in containers.read_batches(
            self.layer0_repo.get_objects,
            lambda data: len(data) == 0,
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

            log.info("Processed batch", done=offset, **ctx)

    def cleanup(self):
        self.pg_storage.disconnect()

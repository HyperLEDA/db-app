from typing import final

import structlog

from app.data import model, repositories
from app.data.repositories.layer0.common import INTERNAL_ID_COLUMN_NAME
from app.lib import containers
from app.lib.storage import postgres
from app.tasks import interface

DEFAULT_BATCH_SIZE = 10000


def _raw_data_last_id_offset(raw: model.Layer0RawData, _: object) -> str:
    return str(raw.data[INTERNAL_ID_COLUMN_NAME].iloc[-1])


@final
class RemoveTableTask(interface.Task):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        table_name: str,
        dry_run: bool = True,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self.log = logger
        self.table_name = table_name
        self.dry_run = dry_run
        self.batch_size = int(batch_size)

    @classmethod
    def name(cls) -> str:
        return "remove-table"

    def prepare(self, config: interface.Config) -> None:
        self.pg_storage = postgres.PgStorage(config.storage, self.log)
        self.pg_storage.connect()
        self.layer0_repository = repositories.Layer0Repository(self.pg_storage, self.log)

    def run(self) -> None:
        if not self.table_name:
            raise ValueError("table_name is required")

        self.log.info(
            "Starting remove-table",
            table_name=self.table_name,
            dry_run=self.dry_run,
            batch_size=self.batch_size,
        )

        total_counts: dict[str, int] = {}
        for _, raw_data in containers.read_batches(
            self.layer0_repository.fetch_raw_data,
            lambda rd: len(rd.data) == 0,
            None,
            _raw_data_last_id_offset,
            table_name=self.table_name,
            columns=[INTERNAL_ID_COLUMN_NAME],
            order_column=INTERNAL_ID_COLUMN_NAME,
            order_direction="asc",
            batch_size=self.batch_size,
        ):
            record_ids = raw_data.data[INTERNAL_ID_COLUMN_NAME].tolist()
            self.log.info("Processing batch", batch_size=len(record_ids))

            if self.dry_run:
                counts = self.layer0_repository.count_records_removal(self.table_name, record_ids)
            else:
                with self.layer0_repository.with_tx():
                    counts = self.layer0_repository.remove_records(self.table_name, record_ids)

            for k, v in counts.items():
                total_counts[k] = total_counts.get(k, 0) + v

        if not self.dry_run:
            with self.layer0_repository.with_tx():
                self.layer0_repository.drop_raw_table(self.table_name)

        self.log.info(
            "remove-table completed",
            table_name=self.table_name,
            counts=total_counts,
            dry_run=self.dry_run,
        )

    def cleanup(self) -> None:
        self.pg_storage.disconnect()

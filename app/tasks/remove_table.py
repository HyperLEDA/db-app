from typing import final

import structlog

from app.data import repositories
from app.lib.storage import postgres
from app.tasks import interface


class DryRunRollback(Exception):
    pass


@final
class RemoveTableTask(interface.Task):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        table_name: str,
        dry_run: bool = True,
    ) -> None:
        self.log = logger
        self.table_name = table_name
        self.dry_run = dry_run

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

        self.log.info("Starting remove-table", table_name=self.table_name, dry_run=self.dry_run)
        try:
            with self.layer0_repository.with_tx():
                counts = self.layer0_repository.remove_table(self.table_name)
                self.log.info("remove-table completed", table_name=self.table_name, counts=counts)
                if self.dry_run:
                    raise DryRunRollback()
        except DryRunRollback:
            self.log.info("remove-table dry run rolled back", table_name=self.table_name)

    def cleanup(self) -> None:
        self.pg_storage.disconnect()

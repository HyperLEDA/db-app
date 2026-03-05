from typing import final

import structlog

from app.data import repositories
from app.lib.storage import postgres
from app.tasks import (
    interface,
    layer2_import_designation,
    layer2_import_icrs,
    layer2_import_nature,
    layer2_import_redshift,
)


@final
class Layer2ImportTask(interface.Task):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        batch_size: int = 100000,
        dry_run: bool = False,
    ) -> None:
        self.log = logger
        self.batch_size = batch_size
        self.dry_run = dry_run

    @classmethod
    def name(cls) -> str:
        return "layer2-import"

    def prepare(self, config: interface.Config) -> None:
        self.pg_storage = postgres.PgStorage(config.storage, self.log)
        self.pg_storage.connect()
        self.layer1_repository = repositories.Layer1Repository(self.pg_storage, self.log)
        self.layer2_repository = repositories.Layer2Repository(self.pg_storage, self.log)

    def run(self) -> None:
        task_classes = [
            layer2_import_designation.Layer2ImportDesignationTask,
            layer2_import_icrs.Layer2ImportICRSTask,
            layer2_import_redshift.Layer2ImportRedshiftTask,
            layer2_import_nature.Layer2ImportNatureTask,
        ]
        for task_cls in task_classes:
            task = task_cls(
                logger=self.log,
                batch_size=self.batch_size,
                dry_run=self.dry_run,
            )
            task.pg_storage = self.pg_storage
            task.layer1_repository = self.layer1_repository
            task.layer2_repository = self.layer2_repository
            task.run()

        self.log.info("Layer 2 import completed")

    def cleanup(self) -> None:
        self.pg_storage.disconnect()

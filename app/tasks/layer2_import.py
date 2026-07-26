import datetime
from collections.abc import Sequence
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

CATALOG_TASKS = {
    "designation": layer2_import_designation.Layer2ImportDesignationTask,
    "icrs": layer2_import_icrs.Layer2ImportICRSTask,
    "redshift": layer2_import_redshift.Layer2ImportRedshiftTask,
    "nature": layer2_import_nature.Layer2ImportNatureTask,
}

DEFAULT_CATALOGS: tuple[str, ...] = ("designation", "icrs", "redshift", "nature")


@final
class Layer2ImportTask(interface.Task):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        batch_size: int = 100000,
        dry_run: bool = False,
        silent: bool = False,
        since: datetime.datetime | str | None = None,
        cleanup_orphans: bool = True,
        catalogs: Sequence[str] | None = None,
    ) -> None:
        self.log = logger
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.silent = silent
        self.since = interface.parse_since(since)
        self.cleanup_orphans = cleanup_orphans
        if catalogs:
            unknown = [c for c in catalogs if c not in CATALOG_TASKS]
            if unknown:
                raise ValueError(f"Unknown catalogs: {', '.join(unknown)}")
            self.catalogs = list(catalogs)
        else:
            self.catalogs = list(DEFAULT_CATALOGS)

    @classmethod
    def name(cls) -> str:
        return "layer2-import"

    def prepare(self, config: interface.Config) -> None:
        self.pg_storage = postgres.PgStorage(config.storage, self.log)
        self.pg_storage.connect()
        self.layer1_repository = repositories.Layer1Repository(self.pg_storage, self.log)
        self.layer2_repository = repositories.Layer2Repository(self.pg_storage, self.log)

    def run(self) -> None:
        for catalog in self.catalogs:
            task_cls = CATALOG_TASKS[catalog]
            task = task_cls(
                logger=self.log,
                batch_size=self.batch_size,
                dry_run=self.dry_run,
                silent=self.silent,
                since=self.since,
                cleanup_orphans=self.cleanup_orphans,
            )
            task.pg_storage = self.pg_storage
            task.layer1_repository = self.layer1_repository
            task.layer2_repository = self.layer2_repository
            task.run()

        self.log.info("Layer 2 import completed", catalogs=self.catalogs)

    def cleanup(self) -> None:
        self.pg_storage.disconnect()

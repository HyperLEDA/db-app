from typing import final

import structlog

from app.data import model, repositories
from app.lib.storage import postgres
from app.tasks import interface

catalogs = [
    model.RawCatalog.ICRS,
    model.RawCatalog.DESIGNATION,
    model.RawCatalog.REDSHIFT,
]


@final
class Layer2OrphanCleanupTask(interface.Task):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        write: bool = False,
    ) -> None:
        self.log = logger
        self.write = write

    @classmethod
    def name(cls) -> str:
        return "layer2-orphan-cleanup"

    def prepare(self, config: interface.Config) -> None:
        self.pg_storage = postgres.PgStorage(config.storage, self.log)
        self.pg_storage.connect()
        self.layer2_repository = repositories.Layer2Repository(self.pg_storage, self.log)

    def run(self) -> None:
        self.log.info("Starting Layer 2 orphan cleanup", write=self.write)
        orphaned = self.layer2_repository.get_orphaned_pgcs(catalogs)
        total = 0
        for table, pgcs in orphaned.items():
            count = len(pgcs)
            total += count
            self.log.info("Orphaned PGCs", table=table, count=count)

        self.log.info("Total orphaned PGCs across layer 2 tables", total=total)

        if self.write:
            pgcs_to_remove = sorted({pgc for pgcs in orphaned.values() for pgc in pgcs})
            self.layer2_repository.remove_pgcs(catalogs, pgcs_to_remove)
            self.log.info("Removed orphaned PGCs from layer 2 tables")

        self.log.info("Layer 2 orphan cleanup completed")

    def cleanup(self) -> None:
        self.pg_storage.disconnect()

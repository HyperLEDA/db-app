from typing import final

import structlog

from app import catalogs
from app.tasks import layer2_common

RAW_CATALOGS = [
    catalogs.RawCatalog.ICRS,
    catalogs.RawCatalog.DESIGNATION,
    catalogs.RawCatalog.REDSHIFT,
    catalogs.RawCatalog.NATURE,
]


@final
class Layer2OrphanCleanupTask(layer2_common.Layer2StorageTask):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        write: bool = False,
    ) -> None:
        super().__init__(logger)
        self.write = write

    @classmethod
    def name(cls) -> str:
        return "layer2-orphan-cleanup"

    def run(self) -> None:
        self.log.info("Starting Layer 2 orphan cleanup", write=self.write)
        orphaned = self.repository.get_orphaned_pgcs(RAW_CATALOGS)
        total = 0
        for table, pgcs in orphaned.items():
            count = len(pgcs)
            total += count
            self.log.info("Orphaned PGCs", table=table, count=count)

        self.log.info("Total orphaned PGCs across layer 2 tables", total=total)

        if self.write:
            pgcs_to_remove = sorted({pgc for pgcs in orphaned.values() for pgc in pgcs})
            self.repository.remove_pgcs(RAW_CATALOGS, pgcs_to_remove)
            self.log.info("Removed orphaned PGCs from layer 2 tables")

        self.log.info("Layer 2 orphan cleanup completed")

import datetime
from typing import final

import structlog

from app.catalogs import layer2
from app.lib import containers
from app.tasks import layer2_common, logging
from app.tasks.layer2_data import aggregation


@final
class Layer2ImportDataTask(layer2_common.Layer2CatalogImportTask):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        batch_size: int = 100000,
        dry_run: bool = False,
        silent: bool = False,
        since: datetime.datetime | str | None = None,
        cleanup_orphans: bool = True,
    ) -> None:
        super().__init__(
            logger,
            batch_size=batch_size,
            dry_run=dry_run,
            silent=silent,
            since=since,
            cleanup_orphans=cleanup_orphans,
        )

    @classmethod
    def name(cls) -> str:
        return "layer2-import-data"

    def run(self) -> None:
        if self.since is not None:
            last_update_dt = self.since
        else:
            last_update_dt = self.repository.get_last_update_time(layer2.Catalog.DATA)
        self.log.info(
            "Starting Layer 2 data import",
            last_update=last_update_dt.ctime(),
            dry_run=self.dry_run,
            cleanup_orphans=self.cleanup_orphans,
        )

        objects_to_save = 0
        removed_pgcs: list[int] = []
        for offset, pgcs in containers.read_batches(
            self.repository.get_changed_pgcs,
            lambda data: len(data) == 0,
            0,
            lambda data, _: int(data[-1]),
            last_update_dt,
            batch_size=self.batch_size,
        ):
            base = self.repository.get_summary_base_rows(pgcs)
            photometry = aggregation.aggregate_bt(self.repository.get_b_photometry(pgcs))
            geometry = aggregation.aggregate_geometry(self.repository.get_b_geometry(pgcs))
            rows = aggregation.assemble_summary(base, photometry, geometry)
            to_save, to_remove = aggregation.partition_rows(rows)
            objects_to_save += len(to_save)
            removed_pgcs.extend(to_remove)
            if not self.dry_run:
                if len(to_save) > 0:
                    self.repository.save(layer2.DataCatalogObject.table(), to_save)
                if to_remove:
                    self.repository.remove_pgcs([layer2.Catalog.DATA], to_remove)
            self.log.info(
                "Processed batch",
                last_pgc=offset,
                batch_size=len(pgcs),
                total_processed=objects_to_save,
            )

        orphans_to_delete = self.finalize_catalog(layer2.Catalog.DATA)
        overlap = self._dry_run_orphan_overlap(removed_pgcs)
        self.log.info("Layer 2 data import completed", last_update=last_update_dt.ctime())

        if not self.silent:
            logging.print_table(
                ("Description", "Count"),
                layer2_common.import_summary_rows(
                    objects_to_save,
                    len(removed_pgcs) + orphans_to_delete - overlap,
                    dry_run=self.dry_run,
                ),
            )

    def _dry_run_orphan_overlap(self, removed_pgcs: list[int]) -> int:
        if not self.dry_run or not self.cleanup_orphans or not removed_pgcs:
            return 0
        orphaned = self.repository.get_orphaned_pgcs([layer2.Catalog.DATA])
        orphan_pgcs = set(orphaned.get(layer2.DataCatalogObject.table(), []))
        return sum(1 for pgc in removed_pgcs if pgc in orphan_pgcs)

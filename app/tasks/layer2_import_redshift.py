import datetime
from typing import final

import numpy as np
import structlog
from astropy import table

from app.data import model
from app.data.schema.layer2 import Redshift
from app.lib import containers
from app.tasks import layer2_common, logging


def aggregate_redshift(tbl: table.QTable) -> table.QTable:
    work = layer2_common.exclude_compilations_with_primary(tbl)

    work["w_cz"] = 1.0 / work["e_cz"] ** 2
    work["cz_w"] = work["cz"] * work["w_cz"]

    grouped = work.group_by("pgc")
    sums = grouped["cz_w", "w_cz"].groups.aggregate(np.sum)

    return table.QTable(
        {
            Redshift.PGC: grouped.groups.keys["pgc"],
            Redshift.CZ: sums["cz_w"] / sums["w_cz"],
            Redshift.E_CZ: sums["w_cz"] ** (-0.5),
        }
    )


@final
class Layer2ImportRedshiftTask(layer2_common.Layer2CatalogImportTask):
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
        return "layer2-import-redshift"

    def run(self) -> None:
        if self.since is not None:
            last_update_dt = self.since
        else:
            last_update_dt = self.layer2_repository.get_last_update_time(model.RawCatalog.REDSHIFT)

        self.log.info(
            "Starting Layer 2 redshift import",
            last_update=last_update_dt.ctime(),
            dry_run=self.dry_run,
            cleanup_orphans=self.cleanup_orphans,
        )

        objects_to_save = 0
        for offset, tbl in containers.read_batches(
            self.layer1_repository.get_new_redshift_records,
            lambda data: len(data) == 0,
            0,
            lambda d, _: int(d["pgc"][-1]),
            last_update_dt,
            batch_size=self.batch_size,
        ):
            agg = aggregate_redshift(tbl)

            if len(agg) > 0:
                objects_to_save += len(agg)
                if not self.dry_run:
                    self.layer2_repository.save("layer2.cz", agg)
            self.log.info(
                "Processed batch",
                last_pgc=offset,
                batch_size=len(tbl),
                total_processed=objects_to_save,
            )

        orphans_to_delete = self.finalize_catalog(model.RawCatalog.REDSHIFT)
        self.log.info("Layer 2 redshift import completed", last_update=last_update_dt.ctime())

        if not self.silent:
            logging.print_table(
                ("Description", "Count"),
                layer2_common.import_summary_rows(objects_to_save, orphans_to_delete, dry_run=self.dry_run),
            )

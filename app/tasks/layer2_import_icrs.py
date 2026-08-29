import datetime
from typing import final

import numpy as np
import structlog
from astropy import table

from app.data import model
from app.data.schema.layer2 import ICRS
from app.lib import containers
from app.tasks import layer2_common, logging


def aggregate_icrs(tbl: table.QTable) -> table.QTable:
    work = layer2_common.exclude_compilations_with_primary(tbl)

    work["w_ra"] = 1.0 / work["e_ra"] ** 2
    work["w_dec"] = 1.0 / work["e_dec"] ** 2
    work["ra_w"] = work["ra"] * work["w_ra"]
    work["dec_w"] = work["dec"] * work["w_dec"]

    grouped = work.group_by("pgc")
    sums = grouped["ra_w", "w_ra", "dec_w", "w_dec"].groups.aggregate(np.sum)

    return table.QTable(
        {
            ICRS.PGC: grouped.groups.keys["pgc"],
            ICRS.RA: sums["ra_w"] / sums["w_ra"],
            ICRS.E_RA: sums["w_ra"] ** (-0.5),
            ICRS.DEC: sums["dec_w"] / sums["w_dec"],
            ICRS.E_DEC: sums["w_dec"] ** (-0.5),
        }
    )


@final
class Layer2ImportICRSTask(layer2_common.Layer2CatalogImportTask):
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
        return "layer2-import-icrs"

    def run(self) -> None:
        if self.since is not None:
            last_update_dt = self.since
        else:
            last_update_dt = self.repository.get_last_update_time(model.RawCatalog.ICRS)
        self.log.info(
            "Starting Layer 2 ICRS import",
            last_update=last_update_dt.ctime(),
            dry_run=self.dry_run,
            cleanup_orphans=self.cleanup_orphans,
        )

        objects_to_save = 0
        for offset, tbl in containers.read_batches(
            self.repository.get_new_icrs_records,
            lambda data: len(data) == 0,
            0,
            lambda d, _: int(d["pgc"][-1]),
            last_update_dt,
            batch_size=self.batch_size,
        ):
            agg = aggregate_icrs(tbl)

            if len(agg) > 0:
                objects_to_save += len(agg)
                if not self.dry_run:
                    self.repository.save("layer2.icrs", agg)

            self.log.info(
                "Processed batch",
                last_pgc=offset,
                batch_size=len(tbl),
                total_processed=objects_to_save,
            )

        orphans_to_delete = self.finalize_catalog(model.RawCatalog.ICRS)
        self.log.info("Layer 2 ICRS import completed", last_update=last_update_dt.ctime())

        if not self.silent:
            logging.print_table(
                ("Description", "Count"),
                layer2_common.import_summary_rows(objects_to_save, orphans_to_delete, dry_run=self.dry_run),
            )

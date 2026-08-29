import datetime
from typing import final

import structlog
from astropy import table

from app.data import model
from app.data.schema.layer2 import Nature
from app.lib import containers
from app.tasks import layer2_common, logging


def aggregate_nature(tbl: table.QTable) -> table.QTable:
    pgcs, type_names = layer2_common.majority_vote_by_pgc(tbl, "type_name")
    return table.QTable({Nature.PGC: pgcs, Nature.TYPE_NAME: type_names})


@final
class Layer2ImportNatureTask(layer2_common.Layer2CatalogImportTask):
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
        return "layer2-import-nature"

    def run(self) -> None:
        if self.since is not None:
            last_update_dt = self.since
        else:
            last_update_dt = self.repository.get_last_update_time(model.RawCatalog.NATURE)
        self.log.info(
            "Starting Layer 2 nature import",
            last_update=last_update_dt.ctime(),
            dry_run=self.dry_run,
            cleanup_orphans=self.cleanup_orphans,
        )

        objects_to_save = 0
        type_distribution: dict[str, int] = {}
        for offset, tbl in containers.read_batches(
            self.repository.get_new_nature_records,
            lambda data: len(data) == 0,
            0,
            lambda d, _: int(d["pgc"][-1]),
            last_update_dt,
            batch_size=self.batch_size,
        ):
            agg = aggregate_nature(tbl)

            for type_name in agg[Nature.TYPE_NAME]:
                key = str(type_name)
                type_distribution[key] = type_distribution.get(key, 0) + 1

            if len(agg) > 0:
                objects_to_save += len(agg)
                if not self.dry_run:
                    self.repository.save("layer2.nature", agg)

            self.log.info(
                "Processed batch",
                last_pgc=offset,
                batch_size=len(tbl),
                total_processed=objects_to_save,
            )

        orphans_to_delete = self.finalize_catalog(model.RawCatalog.NATURE)
        self.log.info("Layer 2 nature import completed", last_update=last_update_dt.ctime())

        if not self.silent:
            type_rows = [(t, c) for t, c in sorted(type_distribution.items())]
            logging.print_table(
                ("Description", "Count"),
                layer2_common.import_summary_rows(objects_to_save, orphans_to_delete, dry_run=self.dry_run),
                sections=[("Distribution by type", [(f"  {t}", c) for t, c in type_rows])] if type_rows else None,
                min_column_widths=(30, 0),
            )

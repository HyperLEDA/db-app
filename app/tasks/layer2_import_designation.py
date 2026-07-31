import datetime
from typing import final

import structlog
from astropy import table

from app.data import enums as data_enums
from app.data import model, repositories
from app.data.schema.layer2 import Designation
from app.lib import containers
from app.lib.storage import postgres
from app.tasks import interface, logging


def aggregate_designation(tbl: table.QTable) -> table.QTable:
    grouped = tbl.group_by("pgc")
    pgcs: list[int] = []
    designs: list[str] = []
    for group in grouped.groups:
        name_counts: dict[str, int] = {}
        for design in group["design"]:
            key = str(design)
            name_counts[key] = name_counts.get(key, 0) + 1
        pgcs.append(int(group["pgc"][0]))
        designs.append(max(name_counts, key=lambda k: name_counts[k]))

    return table.QTable({Designation.PGC: pgcs, Designation.DESIGN: designs})


@final
class Layer2ImportDesignationTask(interface.Task):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        batch_size: int = 100000,
        dry_run: bool = False,
        silent: bool = False,
        since: datetime.datetime | str | None = None,
        cleanup_orphans: bool = True,
    ) -> None:
        self.log = logger
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.silent = silent
        self.since = interface.parse_since(since)
        self.cleanup_orphans = cleanup_orphans

    @classmethod
    def name(cls) -> str:
        return "layer2-import-designation"

    def prepare(self, config: interface.Config) -> None:
        self.pg_storage = postgres.PgStorage(config.storage, self.log, data_enums.PG_ENUM_REGISTRY)
        self.pg_storage.connect()
        self.layer1_repository = repositories.Layer1Repository(self.pg_storage, self.log)
        self.layer2_repository = repositories.Layer2Repository(self.pg_storage, self.log)

    def run(self) -> None:
        if self.since is not None:
            last_update_dt = self.since
        else:
            last_update_dt = self.layer2_repository.get_last_update_time(model.RawCatalog.DESIGNATION)
        self.log.info(
            "Starting Layer 2 designation import",
            last_update=last_update_dt.ctime(),
            dry_run=self.dry_run,
            cleanup_orphans=self.cleanup_orphans,
        )

        objects_to_save = 0
        for offset, tbl in containers.read_batches(
            self.layer1_repository.get_new_designation_records,
            lambda data: len(data) == 0,
            0,
            lambda d, _: int(d["pgc"][-1]),
            last_update_dt,
            batch_size=self.batch_size,
        ):
            agg = aggregate_designation(tbl)
            if len(agg) > 0:
                objects_to_save += len(agg)
                if not self.dry_run:
                    self.layer2_repository.save("layer2.designation", agg)
            self.log.info(
                "Processed batch",
                last_pgc=offset,
                batch_size=len(tbl),
                total_processed=objects_to_save,
            )

        orphans_to_delete = 0
        if self.cleanup_orphans:
            orphaned = self.layer2_repository.get_orphaned_pgcs([model.RawCatalog.DESIGNATION])
            pgcs_to_remove = [pgc for pgcs in orphaned.values() for pgc in pgcs]
            orphans_to_delete = len(pgcs_to_remove)
            if pgcs_to_remove and not self.dry_run:
                self.layer2_repository.remove_pgcs([model.RawCatalog.DESIGNATION], pgcs_to_remove)

        if not self.dry_run:
            self.layer2_repository.update_last_update_time(
                datetime.datetime.now(tz=datetime.UTC), model.RawCatalog.DESIGNATION
            )
        self.log.info("Layer 2 designation import completed", last_update=last_update_dt.ctime())

        if not self.silent:
            logging.print_table(
                ("Description", "Count"),
                [
                    ("Objects saved", objects_to_save),
                    ("Orphans deleted", orphans_to_delete),
                ],
            )

    def cleanup(self) -> None:
        self.pg_storage.disconnect()

import datetime
from typing import final

import structlog

from app.data import model, repositories
from app.lib import containers, logging
from app.lib.storage import postgres
from app.tasks import interface

DESIGNATION_COLUMNS = ["design"]


@final
class Layer2ImportDesignationTask(interface.Task):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        batch_size: int = 100000,
        dry_run: bool = False,
        silent: bool = False,
    ) -> None:
        self.log = logger
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.silent = silent

    @classmethod
    def name(cls) -> str:
        return "layer2-import-designation"

    def prepare(self, config: interface.Config) -> None:
        self.pg_storage = postgres.PgStorage(config.storage, self.log)
        self.pg_storage.connect()
        self.layer1_repository = repositories.Layer1Repository(self.pg_storage, self.log)
        self.layer2_repository = repositories.Layer2Repository(self.pg_storage, self.log)

    def run(self) -> None:
        last_update_dt = self.layer2_repository.get_last_update_time(model.RawCatalog.DESIGNATION)
        self.log.info(
            "Starting Layer 2 designation import",
            last_update=last_update_dt.ctime(),
            dry_run=self.dry_run,
        )

        objects_to_save = 0
        for offset, records in containers.read_batches(
            self.layer1_repository.get_new_designation_records,
            lambda data: len(data) == 0,
            0,
            lambda d, _: d[-1].pgc,
            last_update_dt,
            batch_size=self.batch_size,
        ):
            records_by_pgc = containers.group_by(records, key_func=lambda r: r.pgc)
            pgcs: list[int] = []
            data: list[list[str]] = []
            for pgc, pgc_records in records_by_pgc.items():
                name_counts: dict[str, int] = {}
                for rec in pgc_records:
                    d = rec.data.design
                    name_counts[d] = name_counts.get(d, 0) + 1
                max_name = ""
                for name, count in name_counts.items():
                    if count > name_counts.get(max_name, 0):
                        max_name = name
                pgcs.append(pgc)
                data.append([max_name])
            if pgcs:
                objects_to_save += len(pgcs)
                if not self.dry_run:
                    self.layer2_repository.save("layer2.designation", DESIGNATION_COLUMNS, pgcs, data)
            self.log.info(
                "Processed batch",
                last_pgc=offset,
                batch_size=len(records),
                total_processed=objects_to_save,
            )

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

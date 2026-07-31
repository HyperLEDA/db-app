import datetime
from typing import final

import structlog
from astropy import table

from app.data import enums as data_enums
from app.data import model, repositories
from app.lib import containers
from app.lib.storage import postgres
from app.tasks import interface, logging


def aggregate_nature(tbl: table.QTable) -> table.QTable:
    grouped = tbl.group_by("pgc")
    pgcs: list[int] = []
    type_names: list[str] = []

    for group in grouped.groups:
        type_counts: dict[str, int] = {}
        for type_name in group["type_name"]:
            key = str(type_name)
            type_counts[key] = type_counts.get(key, 0) + 1
        pgcs.append(int(group["pgc"][0]))
        type_names.append(max(type_counts, key=lambda k: type_counts[k]))

    return table.QTable({"pgc": pgcs, "type_name": type_names})


@final
class Layer2ImportNatureTask(interface.Task):
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
        return "layer2-import-nature"

    def prepare(self, config: interface.Config) -> None:
        self.pg_storage = postgres.PgStorage(config.storage, self.log, data_enums.PG_ENUM_REGISTRY)
        self.pg_storage.connect()
        self.layer1_repository = repositories.Layer1Repository(self.pg_storage, self.log)
        self.layer2_repository = repositories.Layer2Repository(self.pg_storage, self.log)

    def run(self) -> None:
        if self.since is not None:
            last_update_dt = self.since
        else:
            last_update_dt = self.layer2_repository.get_last_update_time(model.RawCatalog.NATURE)
        self.log.info(
            "Starting Layer 2 nature import",
            last_update=last_update_dt.ctime(),
            dry_run=self.dry_run,
            cleanup_orphans=self.cleanup_orphans,
        )

        objects_to_save = 0
        type_distribution: dict[str, int] = {}
        for offset, tbl in containers.read_batches(
            self.layer1_repository.get_new_nature_records,
            lambda data: len(data) == 0,
            0,
            lambda d, _: int(d["pgc"][-1]),
            last_update_dt,
            batch_size=self.batch_size,
        ):
            agg = aggregate_nature(tbl)

            for type_name in agg["type_name"]:
                key = str(type_name)
                type_distribution[key] = type_distribution.get(key, 0) + 1

            if len(agg) > 0:
                objects_to_save += len(agg)
                if not self.dry_run:
                    self.layer2_repository.save("layer2.nature", agg)

            self.log.info(
                "Processed batch",
                last_pgc=offset,
                batch_size=len(tbl),
                total_processed=objects_to_save,
            )

        orphans_to_delete = 0
        if self.cleanup_orphans:
            orphaned = self.layer2_repository.get_orphaned_pgcs([model.RawCatalog.NATURE])
            pgcs_to_remove = [pgc for pgcs in orphaned.values() for pgc in pgcs]
            orphans_to_delete = len(pgcs_to_remove)
            if pgcs_to_remove and not self.dry_run:
                self.layer2_repository.remove_pgcs([model.RawCatalog.NATURE], pgcs_to_remove)

        if not self.dry_run:
            self.layer2_repository.update_last_update_time(
                datetime.datetime.now(tz=datetime.UTC), model.RawCatalog.NATURE
            )
        self.log.info("Layer 2 nature import completed", last_update=last_update_dt.ctime())

        if not self.silent:
            type_rows = [(t, c) for t, c in sorted(type_distribution.items())]
            logging.print_table(
                ("Description", "Count"),
                [
                    ("Objects saved", objects_to_save),
                    ("Orphans deleted", orphans_to_delete),
                ],
                sections=[("Distribution by type", [(f"  {t}", c) for t, c in type_rows])] if type_rows else None,
                min_column_widths=(30, 0),
            )

    def cleanup(self) -> None:
        self.pg_storage.disconnect()

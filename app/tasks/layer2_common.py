import abc
import datetime

import numpy as np
import structlog
from astropy import table

from app.data import model, repositories
from app.lib.storage import enums, postgres
from app.tasks import interface


def majority_vote_by_pgc(tbl: table.QTable, value_column: str) -> tuple[list[int], list[str]]:
    grouped = tbl.group_by("pgc")
    pgcs: list[int] = []
    values: list[str] = []
    for group in grouped.groups:
        counts: dict[str, int] = {}
        for value in group[value_column]:
            key = str(value)
            counts[key] = counts.get(key, 0) + 1
        pgcs.append(int(group["pgc"][0]))
        values.append(max(counts, key=lambda k: counts[k]))
    return pgcs, values


def exclude_compilations_with_primary(tbl: table.QTable) -> table.QTable:
    work = table.QTable(tbl, copy=True)
    is_compilation = np.asarray(work["datatype"]) == enums.DataType.COMPILATION.value
    pgc = np.asarray(work["pgc"])
    has_primary = np.isin(pgc, pgc[~is_compilation])
    return work[~is_compilation | ~has_primary]


def import_summary_rows(
    objects_count: int,
    orphans_count: int,
    *,
    dry_run: bool,
) -> list[tuple[str, int]]:
    if dry_run:
        return [
            ("Objects to be saved", objects_count),
            ("Orphans to be deleted", orphans_count),
        ]
    return [
        ("Objects saved", objects_count),
        ("Orphans deleted", orphans_count),
    ]


class Layer2StorageTask(interface.Task, abc.ABC):
    def __init__(self, logger: structlog.stdlib.BoundLogger) -> None:
        self.log = logger

    def prepare(self, config: interface.Config) -> None:
        self.pg_storage = postgres.PgStorage(config.storage, self.log, enums.PG_ENUM_REGISTRY)
        self.pg_storage.connect()
        self.layer2_repository = repositories.Layer2Repository(self.pg_storage, self.log)

    def cleanup(self) -> None:
        self.pg_storage.disconnect()


class Layer2CatalogImportTask(Layer2StorageTask, abc.ABC):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        batch_size: int = 100000,
        dry_run: bool = False,
        silent: bool = False,
        since: datetime.datetime | str | None = None,
        cleanup_orphans: bool = True,
    ) -> None:
        super().__init__(logger)
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.silent = silent
        self.since = interface.parse_since(since)
        self.cleanup_orphans = cleanup_orphans

    def prepare(self, config: interface.Config) -> None:
        super().prepare(config)
        self.layer1_repository = repositories.Layer1Repository(self.pg_storage, self.log)

    def finalize_catalog(self, catalog: model.RawCatalog) -> int:
        orphans_to_delete = 0
        if self.cleanup_orphans:
            orphaned = self.layer2_repository.get_orphaned_pgcs([catalog])
            pgcs_to_remove = [pgc for pgcs in orphaned.values() for pgc in pgcs]
            orphans_to_delete = len(pgcs_to_remove)
            if pgcs_to_remove and not self.dry_run:
                self.layer2_repository.remove_pgcs([catalog], pgcs_to_remove)

        if not self.dry_run:
            self.layer2_repository.update_last_update_time(datetime.datetime.now(tz=datetime.UTC), catalog)
        return orphans_to_delete

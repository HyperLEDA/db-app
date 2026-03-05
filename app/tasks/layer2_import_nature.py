import datetime
from typing import final

import structlog

from app.data import model, repositories
from app.lib import containers
from app.lib.storage import postgres
from app.tasks import interface


@final
class Layer2ImportNatureTask(interface.Task):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        batch_size: int = 10000,
        dry_run: bool = False,
    ) -> None:
        self.log = logger
        self.batch_size = batch_size
        self.dry_run = dry_run

    @classmethod
    def name(cls) -> str:
        return "layer2-import-nature"

    def prepare(self, config: interface.Config) -> None:
        self.pg_storage = postgres.PgStorage(config.storage, self.log)
        self.pg_storage.connect()
        self.layer1_repository = repositories.Layer1Repository(self.pg_storage, self.log)
        self.layer2_repository = repositories.Layer2Repository(self.pg_storage, self.log)

    def run(self) -> None:
        last_update_dt = self.layer2_repository.get_last_update_time(model.RawCatalog.NATURE)
        self.log.info(
            "Starting Layer 2 nature import",
            last_update=last_update_dt.ctime(),
            dry_run=self.dry_run,
        )

        objects_to_save = 0
        type_distribution: dict[str, int] = {}
        for offset, records in containers.read_batches(
            self.layer1_repository.get_new_nature_records,
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
                type_counts: dict[str, int] = {}
                for rec in pgc_records:
                    type_counts[rec.type_name] = type_counts.get(rec.type_name, 0) + 1
                max_type = max(type_counts, key=lambda k: type_counts[k])
                type_distribution[max_type] = type_distribution.get(max_type, 0) + 1
                pgcs.append(pgc)
                data.append([max_type])
            if pgcs:
                objects_to_save += len(pgcs)
                if not self.dry_run:
                    self.layer2_repository.save("layer2.nature", ["type_name"], pgcs, data)
            self.log.info(
                "Processed batch",
                last_pgc=offset,
                batch_size=len(records),
                total_processed=objects_to_save,
            )

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

        if self.dry_run:
            self._print_summary(objects_to_save, orphans_to_delete, type_distribution)

    def _print_summary(
        self,
        objects_to_save: int,
        orphans_to_delete: int,
        type_distribution: dict[str, int],
    ) -> None:
        col_desc = "Description"
        col_count = "Count"
        type_rows = [(t, c) for t, c in sorted(type_distribution.items())]
        width_desc = max(
            len(col_desc),
            30,
            len("Distribution by type"),
            *(len(f"  {t}") for t, _ in type_rows) if type_rows else [0],
        )
        width_count = max(
            len(col_count),
            len(str(objects_to_save)),
            len(str(orphans_to_delete)),
            *(len(str(c)) for _, c in type_rows) if type_rows else [0],
        )
        sep = f"+{'-' * (width_desc + 2)}+{'-' * (width_count + 2)}+"
        lines = [
            sep,
            f"| {col_desc:<{width_desc}} | {col_count:>{width_count}} |",
            sep,
            f"| {'Objects to be saved':<{width_desc}} | {objects_to_save:>{width_count}} |",
            f"| {'Orphans to be deleted':<{width_desc}} | {orphans_to_delete:>{width_count}} |",
            sep,
        ]
        if type_rows:
            lines.append(f"| {'Distribution by type':<{width_desc}} | {'':>{width_count}} |")
            lines.extend([f"| {f'  {t}':<{width_desc}} | {c:>{width_count}} |" for t, c in type_rows])
            lines.append(sep)
        for line in lines:
            print(line)

    def cleanup(self) -> None:
        self.pg_storage.disconnect()

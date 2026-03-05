import datetime
from typing import final

import numpy as np
import pandas as pd
import structlog
from astropy import units as u

from app.data import model, repositories
from app.lib import containers
from app.lib.storage import postgres
from app.tasks import interface

ICRS_COLUMNS = ["ra", "e_ra", "dec", "e_dec"]
DEG = "deg"


def _array_to_deg(arr: np.ndarray, unit_str: str) -> np.ndarray:
    return np.asarray((arr * u.Unit(unit_str)).to(u.Unit(DEG)).value)


def _array_from_deg(arr: np.ndarray, unit_str: str) -> np.ndarray:
    return np.asarray((arr * u.Unit(DEG)).to(u.Unit(unit_str)).value)


@final
class Layer2ImportICRSTask(interface.Task):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        batch_size: int = 100000,
        dry_run: bool = False,
    ) -> None:
        self.log = logger
        self.batch_size = batch_size
        self.dry_run = dry_run

    @classmethod
    def name(cls) -> str:
        return "layer2-import-icrs"

    def prepare(self, config: interface.Config) -> None:
        self.pg_storage = postgres.PgStorage(config.storage, self.log)
        self.pg_storage.connect()
        self.layer1_repository = repositories.Layer1Repository(self.pg_storage, self.log)
        self.layer2_repository = repositories.Layer2Repository(self.pg_storage, self.log)

    def run(self) -> None:
        last_update_dt = self.layer2_repository.get_last_update_time(model.RawCatalog.ICRS)
        layer1_units = self.layer1_repository.get_column_units(model.RawCatalog.ICRS)
        layer2_units = self.layer2_repository.get_column_units("layer2", "icrs")
        self.log.info(
            "Starting Layer 2 ICRS import",
            last_update=last_update_dt.ctime(),
            dry_run=self.dry_run,
        )

        objects_to_save = 0
        for offset, records in containers.read_batches(
            self.layer1_repository.get_new_icrs_records,
            lambda data: len(data) == 0,
            0,
            lambda d, _: d[-1].pgc,
            last_update_dt,
            batch_size=self.batch_size,
        ):
            df = pd.DataFrame(
                [(r.pgc, r.ra, r.e_ra, r.dec, r.e_dec) for r in records],
                columns=["pgc"] + ICRS_COLUMNS,
            )
            for col in ICRS_COLUMNS:
                unit = layer1_units.get(col, DEG)
                df[col] = _array_to_deg(np.asarray(df[col].values), unit)
            agg = df.groupby("pgc", as_index=True)[ICRS_COLUMNS].mean()
            for col in ICRS_COLUMNS:
                unit = layer2_units.get(col, DEG)
                agg[col] = _array_from_deg(np.asarray(agg[col].values), unit)
            pgcs = agg.index.tolist()
            data = agg[ICRS_COLUMNS].values.tolist()

            if pgcs:
                objects_to_save += len(pgcs)
                if not self.dry_run:
                    self.layer2_repository.save("layer2.icrs", ICRS_COLUMNS, pgcs, data)
            self.log.info(
                "Processed batch",
                last_pgc=offset,
                batch_size=len(records),
                total_processed=objects_to_save,
            )

        orphaned = self.layer2_repository.get_orphaned_pgcs([model.RawCatalog.ICRS])
        pgcs_to_remove = [pgc for pgcs in orphaned.values() for pgc in pgcs]
        orphans_to_delete = len(pgcs_to_remove)
        if pgcs_to_remove and not self.dry_run:
            self.layer2_repository.remove_pgcs([model.RawCatalog.ICRS], pgcs_to_remove)

        if not self.dry_run:
            self.layer2_repository.update_last_update_time(
                datetime.datetime.now(tz=datetime.UTC), model.RawCatalog.ICRS
            )
        self.log.info("Layer 2 ICRS import completed", last_update=last_update_dt.ctime())

        if self.dry_run:
            self._print_summary(objects_to_save, orphans_to_delete)

    def _print_summary(self, objects_to_save: int, orphans_to_delete: int) -> None:
        col_desc = "Description"
        col_count = "Count"
        width_desc = max(len(col_desc), 30, len("Objects to be saved"), len("Orphans to be deleted"))
        width_count = max(len(col_count), len(str(objects_to_save)), len(str(orphans_to_delete)))
        sep = f"+{'-' * (width_desc + 2)}+{'-' * (width_count + 2)}+"
        lines = [
            sep,
            f"| {col_desc:<{width_desc}} | {col_count:>{width_count}} |",
            sep,
            f"| {'Objects to be saved':<{width_desc}} | {objects_to_save:>{width_count}} |",
            f"| {'Orphans to be deleted':<{width_desc}} | {orphans_to_delete:>{width_count}} |",
            sep,
        ]
        for line in lines:
            print(line)

    def cleanup(self) -> None:
        self.pg_storage.disconnect()

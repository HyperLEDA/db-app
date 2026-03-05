import datetime
from typing import final

import numpy as np
import pandas as pd
import structlog
from astropy import units as u

from app.data import model, repositories
from app.lib import containers, logging
from app.lib.storage import postgres
from app.tasks import interface

REDSHIFT_COLUMNS = ["cz", "e_cz"]
VELOCITY_UNIT = "m/s"


def _array_to_velocity(arr: np.ndarray, unit_str: str) -> np.ndarray:
    return np.asarray((arr * u.Unit(unit_str)).to(u.Unit(VELOCITY_UNIT)).value)


def _array_from_velocity(arr: np.ndarray, unit_str: str) -> np.ndarray:
    return np.asarray((arr * u.Unit(VELOCITY_UNIT)).to(u.Unit(unit_str)).value)


@final
class Layer2ImportRedshiftTask(interface.Task):
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
        return "layer2-import-redshift"

    def prepare(self, config: interface.Config) -> None:
        self.pg_storage = postgres.PgStorage(config.storage, self.log)
        self.pg_storage.connect()
        self.layer1_repository = repositories.Layer1Repository(self.pg_storage, self.log)
        self.layer2_repository = repositories.Layer2Repository(self.pg_storage, self.log)

    def run(self) -> None:
        last_update_dt = self.layer2_repository.get_last_update_time(model.RawCatalog.REDSHIFT)
        layer1_units = self.layer1_repository.get_column_units(model.RawCatalog.REDSHIFT)
        layer2_units = self.layer2_repository.get_column_units("layer2", "cz")
        self.log.info(
            "Starting Layer 2 redshift import",
            last_update=last_update_dt.ctime(),
            dry_run=self.dry_run,
        )

        objects_to_save = 0
        for offset, records in containers.read_batches(
            self.layer1_repository.get_new_redshift_records,
            lambda data: len(data) == 0,
            0,
            lambda d, _: d[-1].pgc,
            last_update_dt,
            batch_size=self.batch_size,
        ):
            df = pd.DataFrame(
                [(r.pgc, r.cz, r.e_cz) for r in records],
                columns=["pgc"] + REDSHIFT_COLUMNS,
            )
            for col in REDSHIFT_COLUMNS:
                unit = layer1_units.get(col, VELOCITY_UNIT)
                df[col] = _array_to_velocity(np.asarray(df[col].values), unit)
            agg = df.groupby("pgc", as_index=True)[REDSHIFT_COLUMNS].mean()
            for col in REDSHIFT_COLUMNS:
                unit = layer2_units.get(col, VELOCITY_UNIT)
                agg[col] = _array_from_velocity(np.asarray(agg[col].values), unit)
            pgcs = agg.index.tolist()
            data = agg[REDSHIFT_COLUMNS].values.tolist()

            if pgcs:
                objects_to_save += len(pgcs)
                if not self.dry_run:
                    self.layer2_repository.save("layer2.cz", REDSHIFT_COLUMNS, pgcs, data)
            self.log.info(
                "Processed batch",
                last_pgc=offset,
                batch_size=len(records),
                total_processed=objects_to_save,
            )

        orphaned = self.layer2_repository.get_orphaned_pgcs([model.RawCatalog.REDSHIFT])
        pgcs_to_remove = [pgc for pgcs in orphaned.values() for pgc in pgcs]
        orphans_to_delete = len(pgcs_to_remove)
        if pgcs_to_remove and not self.dry_run:
            self.layer2_repository.remove_pgcs([model.RawCatalog.REDSHIFT], pgcs_to_remove)

        if not self.dry_run:
            self.layer2_repository.update_last_update_time(
                datetime.datetime.now(tz=datetime.UTC), model.RawCatalog.REDSHIFT
            )
        self.log.info("Layer 2 redshift import completed", last_update=last_update_dt.ctime())

        logging.print_table(
            ("Description", "Count"),
            [
                ("Objects saved", objects_to_save),
                ("Orphans deleted", orphans_to_delete),
            ],
        )

    def cleanup(self) -> None:
        self.pg_storage.disconnect()

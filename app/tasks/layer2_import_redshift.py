import datetime
from typing import Any, final

import numpy as np
import structlog
from astropy import table
from astropy import units as u

from app.catalogs import layer2
from app.lib import astronomy, containers
from app.tasks import interface, layer2_common, logging
from app.tasks.velocity_config import ApexConfig


def aggregate_redshift(tbl: table.QTable) -> table.QTable:
    work = layer2_common.exclude_compilations_with_primary(tbl)

    work["w_cz"] = 1.0 / work["e_cz"] ** 2
    work["cz_w"] = work["cz"] * work["w_cz"]

    grouped = work.group_by("pgc")
    sums = grouped["cz_w", "w_cz"].groups.aggregate(np.sum)

    return table.QTable(
        {
            "pgc": grouped.groups.keys["pgc"],
            "cz": sums["cz_w"] / sums["w_cz"],
            "e_cz": sums["w_cz"] ** (-0.5),
        }
    )


def build_velocity_rows(
    agg: table.QTable,
    icrs: table.QTable,
    apexes: dict[str, ApexConfig],
) -> table.QTable:
    empty = _empty_velocity_rows()
    if len(agg) == 0 or len(icrs) == 0 or len(apexes) == 0:
        return empty

    agg_pgc = np.asarray(agg["pgc"], dtype=np.int64)
    icrs_pgc = np.asarray(icrs["pgc"], dtype=np.int64)
    order = np.argsort(icrs_pgc, kind="stable")
    sorted_pgc = icrs_pgc[order]
    position = np.searchsorted(sorted_pgc, agg_pgc)
    in_range = position < sorted_pgc.size
    matched = np.zeros(agg_pgc.shape, dtype=bool)
    matched[in_range] = sorted_pgc[position[in_range]] == agg_pgc[in_range]
    if not np.any(matched):
        return empty

    icrs_index = order[position[matched]]
    ra = _column_values(icrs["ra"], "deg")[icrs_index]
    dec = _column_values(icrs["dec"], "deg")[icrs_index]
    e_ra = _column_values(icrs["e_ra"], "deg")[icrs_index]
    e_dec = _column_values(icrs["e_dec"], "deg")[icrs_index]
    lon, lat = astronomy.equatorial_to_galactic_radians(ra, dec)
    e_lon = np.deg2rad(e_ra)
    e_lat = np.deg2rad(e_dec)
    cz = _column_values(agg["cz"], "km/s")[matched]
    e_cz = _column_values(agg["e_cz"], "km/s")[matched]

    keys = list(apexes)
    velocities = np.empty((len(cz), len(keys)))
    errors = np.empty((len(cz), len(keys)))
    for index, key in enumerate(keys):
        apex = apexes[key]
        velocities[:, index], errors[:, index] = astronomy.velocity_wr_apex_batch(
            cz,
            lon,
            lat,
            apex.vel.value,
            np.deg2rad(apex.lon.value),
            np.deg2rad(apex.lat.value),
            e_cz,
            e_lon,
            e_lat,
            apex.vel.error,
            np.deg2rad(apex.lon.error),
            np.deg2rad(apex.lat.error),
        )

    kms = u.Unit("km/s")
    return table.QTable(
        {
            "pgc": np.repeat(agg_pgc[matched], len(keys)),
            "apex": np.tile(np.asarray(keys, dtype=str), len(cz)),
            "v": u.Quantity(velocities.reshape(-1), kms),
            "e_v": u.Quantity(errors.reshape(-1), kms),
        }
    )


def _empty_velocity_rows() -> table.QTable:
    kms = u.Unit("km/s")
    return table.QTable(
        {
            "pgc": np.array([], dtype=np.int64),
            "apex": np.array([], dtype=str),
            "v": u.Quantity(np.array([], dtype=float), kms),
            "e_v": u.Quantity(np.array([], dtype=float), kms),
        }
    )


def _column_values(column: Any, unit: str) -> np.ndarray:
    if isinstance(column, u.Quantity):
        return np.asarray(column.to_value(u.Unit(unit)), dtype=float)
    return np.asarray(column, dtype=float)


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

    def prepare(self, config: interface.Config) -> None:
        super().prepare(config)
        self.apexes = config.catalogs.velocity.apexes

    @classmethod
    def name(cls) -> str:
        return "layer2-import-redshift"

    def _save_velocities(self, agg: table.QTable) -> None:
        pgcs = [int(pgc) for pgc in agg["pgc"]]
        icrs = self.repository.get_layer2_icrs(pgcs)
        velocities = build_velocity_rows(agg, icrs, self.apexes)
        self.repository.save("layer2.velocity", velocities, delete_pgcs=pgcs)

    def run(self) -> None:
        if self.since is not None:
            last_update_dt = self.since
        else:
            last_update_dt = self.repository.get_last_update_time(layer2.Catalog.REDSHIFT)

        self.log.info(
            "Starting Layer 2 redshift import",
            last_update=last_update_dt.ctime(),
            dry_run=self.dry_run,
            cleanup_orphans=self.cleanup_orphans,
        )

        objects_to_save = 0
        for offset, tbl in containers.read_batches(
            self.repository.get_new_redshift_records,
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
                    self.repository.save("layer2.cz", agg)
                    self._save_velocities(agg)
            self.log.info(
                "Processed batch",
                last_pgc=offset,
                batch_size=len(tbl),
                total_processed=objects_to_save,
            )

        orphans_to_delete = self.finalize_catalog(layer2.Catalog.REDSHIFT)
        self.log.info("Layer 2 redshift import completed", last_update=last_update_dt.ctime())

        if not self.silent:
            logging.print_table(
                ("Description", "Count"),
                layer2_common.import_summary_rows(objects_to_save, orphans_to_delete, dry_run=self.dry_run),
            )

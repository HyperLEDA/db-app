import datetime
from typing import Any, final

import numpy as np
import structlog
from astropy import table
from astropy import units as u

from app.catalogs import layer2
from app.lib import astronomy, containers
from app.specs import fieldapi as fieldapi_spec
from app.tasks import layer2_common, layer2_import_icrs, layer2_import_nature, logging
from app.tasks.designation import aggregation

EBV_CHUNK_SIZE = 10_000


def sample_ebv(
    client: fieldapi_spec.FieldAPIClient,
    coordinates: list[tuple[float, float]],
    chunk_size: int = EBV_CHUNK_SIZE,
) -> list[float]:
    if not coordinates:
        return []

    index: dict[tuple[float, float], int] = {}
    unique: list[fieldapi_spec.SkyCoordinate] = []
    for ra, dec in coordinates:
        key = (ra, dec)
        if key not in index:
            index[key] = len(unique)
            unique.append(fieldapi_spec.SkyCoordinate(ra_deg=ra, dec_deg=dec))

    values: list[float] = []
    for start in range(0, len(unique), chunk_size):
        values.extend(client.sample_sfd_ebv(unique[start : start + chunk_size]))
    return [values[index[key]] for key in coordinates]


def assign_ebv(rows: table.QTable, client: fieldapi_spec.FieldAPIClient) -> None:
    coordinates: list[tuple[float, float]] = []
    indexes: list[int] = []
    for i in range(len(rows)):
        ra = rows["ra"][i]
        dec = rows["dec"][i]
        if ra is None or dec is None:
            continue
        coordinates.append((_degrees(ra), _degrees(dec)))
        indexes.append(i)

    ebv: list[float | None] = [None] * len(rows)
    if coordinates:
        sampled = sample_ebv(client, coordinates)
        for i, value in zip(indexes, sampled, strict=True):
            # SFD pixels can be slightly negative; the column check requires ebv >= 0.
            ebv[i] = max(0.0, float(value))
    rows["ebv"] = np.array(ebv, dtype=object)


def build_object_rows(
    pgcs: list[int],
    designations: table.QTable,
    natures: table.QTable,
    icrs: table.QTable,
    err_types: set[str],
) -> tuple[table.QTable, list[int]]:
    designation_by_pgc = _designation_by_pgc(designations)
    nature_by_pgc = _nature_by_pgc(natures)
    icrs_by_pgc = _icrs_by_pgc(icrs)

    keep_pgcs: list[int] = []
    names: list[str] = []
    objtypes: list[str | None] = []
    ras: list[float | None] = []
    e_ras: list[float | None] = []
    decs: list[float | None] = []
    e_decs: list[float | None] = []
    longs: list[float | None] = []
    lats: list[float | None] = []
    sgls: list[float | None] = []
    sgbs: list[float | None] = []
    to_delete: list[int] = []

    for pgc in pgcs:
        name = designation_by_pgc.get(pgc)
        objtype = nature_by_pgc.get(pgc)
        if name is None or (objtype is not None and objtype in err_types):
            to_delete.append(pgc)
            continue

        keep_pgcs.append(pgc)
        names.append(name)
        objtypes.append(objtype)
        icrs_row = icrs_by_pgc.get(pgc)
        if icrs_row is None:
            ras.append(None)
            e_ras.append(None)
            decs.append(None)
            e_decs.append(None)
            longs.append(None)
            lats.append(None)
            sgls.append(None)
            sgbs.append(None)
            continue

        ra = _degrees(icrs_row["ra"])
        e_ra = _degrees(icrs_row["e_ra"])
        dec = _degrees(icrs_row["dec"])
        e_dec = _degrees(icrs_row["e_dec"])
        lon, lat, _, _ = astronomy.equatorial_to_lonlat(ra, dec, e_ra, e_dec, "galactic")
        sgl, sgb, _, _ = astronomy.equatorial_to_lonlat(ra, dec, e_ra, e_dec, "supergalactic")
        ras.append(ra)
        e_ras.append(e_ra)
        decs.append(dec)
        e_decs.append(e_dec)
        longs.append(lon)
        lats.append(lat)
        sgls.append(sgl)
        sgbs.append(sgb)

    rows = table.QTable(
        {
            "pgc": keep_pgcs,
            "name": names,
            "objtype": np.array(objtypes, dtype=object),
            "ra": np.array(ras, dtype=object),
            "e_ra": np.array(e_ras, dtype=object),
            "dec": np.array(decs, dtype=object),
            "e_dec": np.array(e_decs, dtype=object),
            "l": np.array(longs, dtype=object),
            "b": np.array(lats, dtype=object),
            "sgl": np.array(sgls, dtype=object),
            "sgb": np.array(sgbs, dtype=object),
            "ebv": np.array([None] * len(keep_pgcs), dtype=object),
        }
    )
    return rows, to_delete


def _designation_by_pgc(tbl: table.QTable) -> dict[int, str]:
    if len(tbl) == 0:
        return {}
    agg = aggregation.aggregate_designation(tbl)
    return {int(pgc): str(name) for pgc, name in zip(agg["pgc"], agg["design"], strict=True)}


def _nature_by_pgc(tbl: table.QTable) -> dict[int, str]:
    if len(tbl) == 0:
        return {}
    agg = layer2_import_nature.aggregate_nature(tbl)
    return {int(pgc): str(type_name) for pgc, type_name in zip(agg["pgc"], agg["type_name"], strict=True)}


def _icrs_by_pgc(tbl: table.QTable) -> dict[int, dict[str, Any]]:
    if len(tbl) == 0:
        return {}
    agg = layer2_import_icrs.aggregate_icrs(tbl)
    return {
        int(agg["pgc"][i]): {
            "ra": agg["ra"][i],
            "e_ra": agg["e_ra"][i],
            "dec": agg["dec"][i],
            "e_dec": agg["e_dec"][i],
        }
        for i in range(len(agg))
    }


def _degrees(value: Any) -> float:
    unit = getattr(value, "unit", None)
    if unit is not None:
        return float(value.to(u.Unit("deg")).value)
    return float(value)


@final
class Layer2ImportObjectsTask(layer2_common.Layer2CatalogImportTask):
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
        return "layer2-import-objects"

    def run(self) -> None:
        if self.since is not None:
            last_update_dt = self.since
        else:
            last_update_dt = self.repository.get_last_update_time(layer2.Catalog.OBJECTS)

        self.log.info(
            "Starting Layer 2 objects import",
            last_update=last_update_dt.ctime(),
            dry_run=self.dry_run,
            cleanup_orphans=self.cleanup_orphans,
        )

        err_types = self.repository.get_error_object_types()
        objects_to_save = 0
        for offset, pgcs_tbl in containers.read_batches(
            self.repository.get_modified_object_pgcs,
            lambda data: len(data) == 0,
            0,
            lambda d, _: int(d["pgc"][-1]),
            last_update_dt,
            batch_size=self.batch_size,
        ):
            pgcs = [int(pgc) for pgc in pgcs_tbl["pgc"]]
            rows, to_delete = build_object_rows(
                pgcs,
                self.repository.get_designation_records_for_pgcs(pgcs),
                self.repository.get_nature_records_for_pgcs(pgcs),
                self.repository.get_icrs_records_for_pgcs(pgcs),
                err_types,
            )
            if len(rows) > 0:
                assign_ebv(rows, self.fieldapi_client)
                objects_to_save += len(rows)
                if not self.dry_run:
                    self.repository.save("layer2.objects", rows)
            if to_delete and not self.dry_run:
                self.repository.remove_pgcs([layer2.Catalog.OBJECTS], to_delete)

            self.log.info(
                "Processed batch",
                last_pgc=offset,
                batch_size=len(pgcs_tbl),
                total_processed=objects_to_save,
            )

        orphans_to_delete = self.finalize_catalog(layer2.Catalog.OBJECTS)
        self.log.info("Layer 2 objects import completed", last_update=last_update_dt.ctime())

        if not self.silent:
            logging.print_table(
                ("Description", "Count"),
                layer2_common.import_summary_rows(objects_to_save, orphans_to_delete, dry_run=self.dry_run),
            )

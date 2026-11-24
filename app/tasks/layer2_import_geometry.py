import datetime
import math
from typing import final

import numpy as np
import structlog
from astropy import table

from app.catalogs import layer2
from app.lib import containers
from app.tasks import layer2_common, logging

_OPTICAL_WAVEREF_MAX_A = 15000.0
_B_BAND = "B"
_D25 = "d25"
_RE = "re"

_EMPTY = {
    "pgc": [],
    "a25": [],
    "b25": [],
    "pa25": [],
    "a_re": [],
    "b_re": [],
    "pa_re": [],
}


def circular_mean_pa(values: np.ndarray) -> float:
    doubled = np.deg2rad(np.asarray(values, dtype=float) * 2.0)
    angle = math.atan2(float(np.mean(np.sin(doubled))), float(np.mean(np.cos(doubled))))
    pa = math.degrees(angle) / 2.0
    pa = math.fmod(pa, 180.0)
    if pa < 0.0:
        pa += 180.0
    if pa >= 180.0:
        return 0.0
    return pa


def _mean_axes(work: table.QTable, *, prefer_b: bool) -> tuple[float, float, float] | None:
    if len(work) == 0:
        return None
    filtered = layer2_common.exclude_compilations_with_primary(work)
    if len(filtered) == 0:
        return None
    if prefer_b:
        bands = np.asarray(filtered["band"], dtype=str)
        b_rows = filtered[bands == _B_BAND]
        if len(b_rows) > 0:
            filtered = b_rows
    return (
        float(np.mean(np.asarray(filtered["a"], dtype=float))),
        float(np.mean(np.asarray(filtered["b"], dtype=float))),
        circular_mean_pa(np.asarray(filtered["pa"], dtype=float)),
    )


def aggregate_geometry(tbl: table.QTable) -> table.QTable:
    if len(tbl) == 0:
        return table.QTable(_EMPTY)

    optical = tbl[np.asarray(tbl["waveref"], dtype=float) < _OPTICAL_WAVEREF_MAX_A]
    if len(optical) == 0:
        return table.QTable(_EMPTY)

    grouped = optical.group_by("pgc")
    pgcs: list[int] = []
    a25s: list[float | None] = []
    b25s: list[float | None] = []
    pa25s: list[float | None] = []
    a_res: list[float | None] = []
    b_res: list[float | None] = []
    pa_res: list[float | None] = []
    for group in grouped.groups:
        kind = np.asarray(group["kind"], dtype=str)
        d25 = _mean_axes(group[kind == _D25], prefer_b=True)
        re = _mean_axes(group[kind == _RE], prefer_b=False)
        if d25 is None and re is None:
            continue
        pgcs.append(int(group["pgc"][0]))
        a25s.append(None if d25 is None else d25[0])
        b25s.append(None if d25 is None else d25[1])
        pa25s.append(None if d25 is None else d25[2])
        a_res.append(None if re is None else re[0])
        b_res.append(None if re is None else re[1])
        pa_res.append(None if re is None else re[2])

    if not pgcs:
        return table.QTable(_EMPTY)

    result = table.QTable()
    result["pgc"] = pgcs
    result["a25"] = np.array(a25s, dtype=object)
    result["b25"] = np.array(b25s, dtype=object)
    result["pa25"] = np.array(pa25s, dtype=object)
    result["a_re"] = np.array(a_res, dtype=object)
    result["b_re"] = np.array(b_res, dtype=object)
    result["pa_re"] = np.array(pa_res, dtype=object)
    return result


@final
class Layer2ImportGeometryTask(layer2_common.Layer2CatalogImportTask):
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
        return "layer2-import-geometry"

    def run(self) -> None:
        last_update_dt = self.start_run(layer2.Catalog.GEOMETRY)

        self.log.info(
            "Starting Layer 2 geometry import",
            last_update=last_update_dt.ctime(),
            dry_run=self.dry_run,
            cleanup_orphans=self.cleanup_orphans,
        )

        objects_to_save = 0
        for offset, tbl in containers.read_batches(
            self.repository.get_new_geometry_records,
            lambda data: len(data) == 0,
            0,
            lambda d, _: int(d["pgc"][-1]),
            last_update_dt,
            batch_size=self.batch_size,
        ):
            with layer2_common.trace_batch(self.name(), offset=offset, input_size=len(tbl)) as span:
                agg = aggregate_geometry(tbl)
                saved = len(agg)
                if saved > 0:
                    objects_to_save += saved
                    if not self.dry_run:
                        self.repository.save("layer2.geometry", agg)
                span.set_attribute("batch.objects_saved", saved)
                span.set_attribute("batch.total_processed", objects_to_save)
            self.log.info(
                "Processed batch",
                last_pgc=offset,
                batch_size=len(tbl),
                total_processed=objects_to_save,
            )

        orphans_to_delete = self.finalize_catalog(layer2.Catalog.GEOMETRY)
        self.log.info("Layer 2 geometry import completed", last_update=last_update_dt.ctime())

        if not self.silent:
            logging.print_table(
                ("Description", "Count"),
                layer2_common.import_summary_rows(objects_to_save, orphans_to_delete, dry_run=self.dry_run),
            )

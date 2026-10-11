from typing import Any

import numpy as np
from astropy import table

from app.tasks import layer2_common

B_BAND = "B"
BT_METHOD = "asymptotic"
GEOMETRY_METHODS = ("isophotal", "visual")
ISOPHOTE_LEVEL = 25.0
QUALITY = "regular"
DEFAULT_E_MAG = 0.3

_SUMMARY_COLUMNS = ["design", "ra", "e_ra", "dec", "e_dec", "type_name", "bt", "e_bt", "d25", "ba"]
_FLOAT_COLUMNS = ("ra", "e_ra", "dec", "e_dec", "bt", "e_bt", "d25", "ba")
_TEXT_COLUMNS = ("design", "type_name")


def aggregate_bt(tbl: table.QTable) -> table.QTable:
    if len(tbl) == 0:
        return _empty_table(["pgc", "bt", "e_bt"])
    work = layer2_common.exclude_compilations_with_primary(tbl)
    if len(work) == 0:
        return _empty_table(["pgc", "bt", "e_bt"])

    pgc = np.asarray(work["pgc"], dtype=np.int64)
    mag = _as_float(work["mag"])
    e_mag = _as_float(work["e_mag"])
    e_mag = np.where(np.isfinite(e_mag), e_mag, DEFAULT_E_MAG)
    weights = 1.0 / np.square(e_mag)
    keys, weight_sum = _sum_by_pgc(pgc, weights)
    _, mag_sum = _sum_by_pgc(pgc, mag * weights)
    return table.QTable(
        {
            "pgc": keys,
            "bt": mag_sum / weight_sum,
            "e_bt": np.power(weight_sum, -0.5),
        }
    )


def aggregate_geometry(tbl: table.QTable) -> table.QTable:
    if len(tbl) == 0:
        return _empty_table(["pgc", "d25", "ba"])
    work = layer2_common.exclude_compilations_with_primary(tbl)
    if len(work) == 0:
        return _empty_table(["pgc", "d25", "ba"])

    pgc = np.asarray(work["pgc"], dtype=np.int64)
    semi_major = _as_float(work["a"])
    semi_minor = _as_float(work["b"])
    d25_ok = np.isfinite(semi_major) & (semi_major > 0)
    ba_ok = d25_ok & np.isfinite(semi_minor) & (semi_minor > 0) & (semi_minor <= semi_major)
    d25_pgc, d25 = _log_mean_by_pgc(pgc[d25_ok], np.log10(2.0 * semi_major[d25_ok]))
    ba_pgc, ba = _log_mean_by_pgc(pgc[ba_ok], np.log10(semi_minor[ba_ok] / semi_major[ba_ok]))
    return _merge_geometry(d25_pgc, d25, ba_pgc, ba)


def assemble_summary(base: table.QTable, photometry: table.QTable, geometry: table.QTable) -> table.QTable:
    if len(base) == 0:
        return _empty_table(["pgc", *_SUMMARY_COLUMNS])
    pgcs = np.asarray(base["pgc"], dtype=np.int64)
    return table.QTable(
        {
            "pgc": pgcs,
            "design": base["design"],
            "ra": _as_float(base["ra"]),
            "e_ra": _as_float(base["e_ra"]),
            "dec": _as_float(base["dec"]),
            "e_dec": _as_float(base["e_dec"]),
            "type_name": base["type_name"],
            "bt": _align_float(photometry, "bt", pgcs),
            "e_bt": _align_float(photometry, "e_bt", pgcs),
            "d25": _align_float(geometry, "d25", pgcs),
            "ba": _align_float(geometry, "ba", pgcs),
        }
    )


def partition_rows(tbl: table.QTable) -> tuple[table.QTable, list[int]]:
    if len(tbl) == 0:
        return tbl, []
    present = np.zeros(len(tbl), dtype=bool)
    for column in _FLOAT_COLUMNS:
        present |= np.isfinite(_as_float(tbl[column]))
    for column in _TEXT_COLUMNS:
        present |= _text_present(tbl[column])
    removed = [int(pgc) for pgc in np.asarray(tbl["pgc"], dtype=np.int64)[~present]]
    return tbl[present], removed


def _sum_by_pgc(pgc: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    order = np.argsort(pgc, kind="mergesort")
    sorted_pgc = pgc[order]
    starts = np.concatenate((np.array([0], dtype=int), np.flatnonzero(np.diff(sorted_pgc)) + 1))
    return sorted_pgc[starts], np.add.reduceat(values[order], starts)


def _log_mean_by_pgc(pgc: np.ndarray, logs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if pgc.size == 0:
        return np.array([], dtype=np.int64), np.array([], dtype=float)
    keys, total = _sum_by_pgc(pgc, logs)
    _, count = _sum_by_pgc(pgc, np.ones(pgc.size, dtype=float))
    return keys, np.power(10.0, total / count)


def _merge_geometry(
    d25_pgc: np.ndarray,
    d25: np.ndarray,
    ba_pgc: np.ndarray,
    ba: np.ndarray,
) -> table.QTable:
    if d25_pgc.size == 0 and ba_pgc.size == 0:
        return _empty_table(["pgc", "d25", "ba"])
    pgcs = np.union1d(d25_pgc, ba_pgc)
    return table.QTable(
        {
            "pgc": pgcs,
            "d25": _align_sorted(d25_pgc, d25, pgcs),
            "ba": _align_sorted(ba_pgc, ba, pgcs),
        }
    )


def _align_float(source: table.QTable, column: str, target_pgc: np.ndarray) -> np.ndarray:
    if len(source) == 0:
        return np.full(target_pgc.shape, np.nan)
    source_pgc = np.asarray(source["pgc"], dtype=np.int64)
    order = np.argsort(source_pgc, kind="mergesort")
    return _align_sorted(source_pgc[order], _as_float(source[column])[order], target_pgc)


def _align_sorted(source_pgc: np.ndarray, source_values: np.ndarray, target_pgc: np.ndarray) -> np.ndarray:
    aligned = np.full(target_pgc.shape, np.nan, dtype=float)
    if source_pgc.size == 0:
        return aligned
    index = np.searchsorted(source_pgc, target_pgc)
    in_range = index < source_pgc.size
    clipped = np.minimum(index, source_pgc.size - 1)
    matched = in_range & (source_pgc[clipped] == target_pgc)
    aligned[matched] = source_values[clipped[matched]]
    return aligned


def _as_float(col: Any) -> np.ndarray:
    mask = getattr(col, "mask", None)
    if mask is not None and np.ndim(mask) > 0:
        data = np.array(np.ma.getdata(col), dtype=float, copy=True)
        data[np.asarray(mask, dtype=bool)] = np.nan
        return data
    if np.ma.isMaskedArray(col):
        return np.asarray(np.ma.filled(col.astype(float), np.nan), dtype=float)
    values = np.asarray(col, dtype=object)
    converted = np.empty(values.shape, dtype=float)
    for index, value in np.ndenumerate(values):
        converted[index] = np.nan if value is None else float(value)
    return converted


def _text_present(col: Any) -> np.ndarray:
    mask = getattr(col, "mask", None)
    values = np.asarray(np.ma.getdata(col) if np.ma.isMaskedArray(col) else col, dtype=object)
    present = np.fromiter((value is not None for value in values.flat), dtype=bool, count=values.size)
    present = present.reshape(values.shape)
    if mask is not None and np.ndim(mask) > 0:
        present &= ~np.asarray(mask, dtype=bool)
    return present


def _empty_table(names: list[str]) -> table.QTable:
    return table.QTable({name: [] for name in names})

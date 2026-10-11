import math

import numpy as np
import pytest
from astropy import table

from app.tasks.data import aggregation


def _bt_table(
    pgcs: list[int],
    mags: list[float],
    errors: list[float | None],
    datatypes: list[str],
) -> table.QTable:
    return table.QTable(
        {
            "pgc": pgcs,
            "mag": mags,
            "e_mag": [np.nan if error is None else error for error in errors],
            "datatype": datatypes,
        }
    )


def _geometry_table(
    pgcs: list[int],
    semi_major: list[float | None],
    semi_minor: list[float | None],
    datatypes: list[str],
) -> table.QTable:
    return table.QTable(
        {
            "pgc": pgcs,
            "a": [np.nan if value is None else value for value in semi_major],
            "b": [np.nan if value is None else value for value in semi_minor],
            "datatype": datatypes,
        }
    )


def test_weighted_bt_and_error() -> None:
    result = aggregation.aggregate_bt(
        _bt_table(
            [1, 1, 2],
            [10.0, 12.0, 15.0],
            [0.1, 0.2, 0.1],
            ["regular", "regular", "regular"],
        )
    )
    by_pgc = {int(pgc): index for index, pgc in enumerate(result["pgc"])}
    assert float(result["bt"][by_pgc[1]]) == pytest.approx((10.0 / 0.1**2 + 12.0 / 0.2**2) / (1 / 0.1**2 + 1 / 0.2**2))
    assert float(result["e_bt"][by_pgc[1]]) == pytest.approx((1 / 0.1**2 + 1 / 0.2**2) ** -0.5)
    assert float(result["bt"][by_pgc[2]]) == pytest.approx(15.0)
    assert float(result["e_bt"][by_pgc[2]]) == pytest.approx(0.1)


def test_missing_e_mag_uses_default() -> None:
    result = aggregation.aggregate_bt(_bt_table([1], [10.0], [None], ["regular"]))
    assert float(result["bt"][0]) == pytest.approx(10.0)
    assert float(result["e_bt"][0]) == pytest.approx(aggregation.DEFAULT_E_MAG)


def test_d25_and_ba_are_log_means() -> None:
    result = aggregation.aggregate_geometry(
        _geometry_table(
            [1, 1],
            [10.0, 40.0],
            [5.0, 8.0],
            ["regular", "regular"],
        )
    )
    assert len(result) == 1
    assert float(result["d25"][0]) == pytest.approx(math.sqrt(20.0 * 80.0))
    assert float(result["ba"][0]) == pytest.approx(math.sqrt(0.5 * 0.2))


def test_compilations_dropped_when_primary_exists() -> None:
    result = aggregation.aggregate_bt(
        _bt_table(
            [1, 1, 2, 2],
            [10.0, 99.0, 10.0, 12.0],
            [0.1, 0.1, 0.1, 0.1],
            ["regular", "compilation", "compilation", "compilation"],
        )
    )
    by_pgc = {int(pgc): float(bt) for pgc, bt in zip(result["pgc"], result["bt"], strict=True)}
    assert by_pgc[1] == pytest.approx(10.0)
    assert by_pgc[2] == pytest.approx(11.0)


def test_only_semi_major_leaves_ba_null() -> None:
    result = aggregation.aggregate_geometry(_geometry_table([1, 2], [10.0, 20.0], [None, 10.0], ["regular", "regular"]))
    by_pgc = {int(pgc): index for index, pgc in enumerate(result["pgc"])}
    assert float(result["d25"][by_pgc[1]]) == pytest.approx(20.0)
    assert math.isnan(float(result["ba"][by_pgc[1]]))
    assert float(result["ba"][by_pgc[2]]) == pytest.approx(0.5)


def test_pgc_without_qualifying_rows_is_absent() -> None:
    assert len(aggregation.aggregate_bt(table.QTable({"pgc": [], "mag": [], "e_mag": [], "datatype": []}))) == 0
    result = aggregation.aggregate_geometry(_geometry_table([1], [None], [None], ["regular"]))
    assert len(result) == 0

import datetime
from unittest import mock

import pytest
import structlog
from astropy import table
from astropy import units as u

from app.tasks import (
    interface,
    layer2_common,
    layer2_import,
    layer2_import_morphology,
    layer2_import_redshift,
)


def _redshift_table(pgc: list[int], cz: list[float], e_cz: list[float], datatype: list[str]) -> table.QTable:
    kms = u.Unit("km/s")
    return table.QTable({"pgc": pgc, "cz": cz * kms, "e_cz": e_cz * kms, "datatype": datatype})


def _morphology_table(
    pgc: list[int],
    t: list[float],
    em: list[float | None],
    ep: list[float | None],
    datatype: list[str],
) -> table.QTable:
    return table.QTable({"pgc": pgc, "t": t, "em": em, "ep": ep, "datatype": datatype})


@pytest.mark.parametrize(
    ("rows", "expected_cz"),
    [
        (_redshift_table([1, 1], [1000.0, 2000.0], [10.0, 20.0], ["regular", "regular"]), 1200.0),
        (
            _redshift_table(
                [1, 1, 1], [1000.0, 2000.0, 5000.0], [10.0, 20.0, 1.0], ["regular", "preliminary", "compilation"]
            ),
            1200.0,
        ),
        (_redshift_table([1, 1], [1000.0, 2000.0], [10.0, 20.0], ["compilation", "compilation"]), 1200.0),
    ],
)
def test_aggregate_redshift(rows: table.QTable, expected_cz: float) -> None:
    agg = layer2_import_redshift.aggregate_redshift(rows)
    assert len(agg) == 1
    assert float(agg["cz"][0].to_value(u.Unit("km/s"))) == pytest.approx(expected_cz)


def test_weighted_mean_cz_error() -> None:
    agg = layer2_import_redshift.aggregate_redshift(
        _redshift_table([1, 1], [1000.0, 2000.0], [10.0, 20.0], ["regular", "regular"])
    )
    formal_err = (1.0 / 10.0**2 + 1.0 / 20.0**2) ** (-0.5)
    assert float(agg["e_cz"][0].to_value(u.Unit("km/s"))) == pytest.approx(formal_err)


def test_redshift_per_pgc_compilation_filtering() -> None:
    agg = layer2_import_redshift.aggregate_redshift(
        _redshift_table(
            [1, 1, 2, 2],
            [1000.0, 5000.0, 1000.0, 2000.0],
            [10.0, 1.0, 10.0, 20.0],
            ["regular", "compilation", "compilation", "compilation"],
        )
    )
    by_pgc = {int(pgc): i for i, pgc in enumerate(agg["pgc"])}
    assert float(agg["cz"][by_pgc[1]].to_value(u.Unit("km/s"))) == pytest.approx(1000.0)
    assert float(agg["cz"][by_pgc[2]].to_value(u.Unit("km/s"))) == pytest.approx(1200.0)


@pytest.mark.parametrize(
    ("rows", "expected_t"),
    [
        (_morphology_table([1, 1], [1.0, 3.0], [0.2, 0.4], [0.6, 0.8], ["regular", "regular"]), 2.0),
        (
            _morphology_table(
                [1, 1, 1], [1.0, 3.0, 9.0], [0.2, 0.4, 0.1], [0.2, 0.4, 0.1], ["regular", "preliminary", "compilation"]
            ),
            2.0,
        ),
        (_morphology_table([1, 1], [1.0, 3.0], [0.2, 0.4], [0.2, 0.4], ["compilation", "compilation"]), 2.0),
    ],
)
def test_aggregate_morphology(rows: table.QTable, expected_t: float) -> None:
    agg = layer2_import_morphology.aggregate_morphology(rows)
    assert len(agg) == 1
    assert float(agg["t"][0]) == pytest.approx(expected_t)


def test_mean_morphology_errors() -> None:
    agg = layer2_import_morphology.aggregate_morphology(
        _morphology_table([1, 1], [1.0, 3.0], [0.2, 0.4], [0.6, 0.8], ["regular", "regular"])
    )
    assert float(agg["em"][0]) == pytest.approx(0.3)
    assert float(agg["ep"][0]) == pytest.approx(0.7)


def test_morphology_per_pgc_compilation_filtering() -> None:
    agg = layer2_import_morphology.aggregate_morphology(
        _morphology_table(
            [1, 1, 2, 2],
            [1.0, 9.0, 1.0, 3.0],
            [0.2, 0.1, 0.2, 0.4],
            [0.2, 0.1, 0.2, 0.4],
            ["regular", "compilation", "compilation", "compilation"],
        )
    )
    by_pgc = {int(pgc): i for i, pgc in enumerate(agg["pgc"])}
    assert float(agg["t"][by_pgc[1]]) == pytest.approx(1.0)
    assert float(agg["t"][by_pgc[2]]) == pytest.approx(2.0)


def test_morphology_null_uncertainties() -> None:
    agg = layer2_import_morphology.aggregate_morphology(
        _morphology_table(
            [1, 1, 2, 2],
            [1.0, 3.0, 4.0, 6.0],
            [0.2, None, None, None],
            [0.4, None, None, None],
            ["regular", "regular", "regular", "regular"],
        )
    )
    by_pgc = {int(pgc): i for i, pgc in enumerate(agg["pgc"])}
    assert float(agg["em"][by_pgc[1]]) == pytest.approx(0.2)
    assert float(agg["ep"][by_pgc[1]]) == pytest.approx(0.4)
    assert agg["em"][by_pgc[2]] is None
    assert agg["ep"][by_pgc[2]] is None


@pytest.mark.parametrize(
    ("catalogs", "expected"),
    [
        (None, list(layer2_import.DEFAULT_CATALOGS)),
        (["morphology"], ["morphology"]),
        (["objects", "redshift"], ["objects", "redshift"]),
    ],
)
def test_layer2_import_catalogs(catalogs: list[str] | None, expected: list[str]) -> None:
    task = layer2_import.Layer2ImportTask(structlog.get_logger(), catalogs=catalogs)
    assert task.catalogs == expected
    if catalogs is None:
        assert "morphology" in task.catalogs


def test_unknown_catalog_raises() -> None:
    with pytest.raises(ValueError):
        layer2_import.Layer2ImportTask(structlog.get_logger(), catalogs=["objects", "nope"])


def test_majority_type_name() -> None:
    tbl = table.QTable({"pgc": [1, 1, 1, 2], "type_name": ["G", "G", "*", "QSO"]})
    pgcs, type_names = layer2_common.majority_vote_by_pgc(tbl, "type_name")
    by_pgc = {int(pgc): str(type_name) for pgc, type_name in zip(pgcs, type_names, strict=True)}
    assert by_pgc[1] == "G" and by_pgc[2] == "QSO"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (datetime.datetime(2020, 1, 2, 3, 4, 5), datetime.datetime(2020, 1, 2, 3, 4, 5, tzinfo=datetime.UTC)),  # noqa: DTZ001
        (
            datetime.datetime(2020, 1, 2, 3, 4, 5, tzinfo=datetime.UTC),
            datetime.datetime(2020, 1, 2, 3, 4, 5, tzinfo=datetime.UTC),
        ),
        ("2020-01-02T03:04:05Z", datetime.datetime(2020, 1, 2, 3, 4, 5, tzinfo=datetime.UTC)),
    ],
)
def test_parse_since(value: datetime.datetime | str | None, expected: datetime.datetime | None) -> None:
    got = interface.parse_since(value)
    if value is not None and isinstance(value, datetime.datetime) and value.tzinfo is not None:
        assert got is value
    else:
        assert got == expected


def test_run_passes_params_to_selected_catalogs() -> None:
    since = datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)
    task = layer2_import.Layer2ImportTask(
        structlog.get_logger(),
        batch_size=10,
        dry_run=True,
        since=since,
        cleanup_orphans=False,
        catalogs=["objects"],
    )
    task.pg_storage = mock.Mock()
    task.repository = mock.Mock()
    task.fieldapi_client = mock.Mock()
    objects_cls = mock.Mock()
    child = mock.Mock()
    objects_cls.return_value = child
    with mock.patch.dict(layer2_import.CATALOG_TASKS, {"objects": objects_cls}):
        task.run()
    objects_cls.assert_called_once_with(
        logger=task.log,
        batch_size=10,
        dry_run=True,
        silent=False,
        since=since,
        cleanup_orphans=False,
    )
    child.run.assert_called_once_with()
    assert child.fieldapi_client is task.fieldapi_client


def _velocity_inputs() -> tuple[table.QTable, table.QTable]:
    kms = u.Unit("km/s")
    deg = u.Unit("deg")
    agg = table.QTable({"pgc": [1, 2], "cz": [1000.0, 2000.0] * kms, "e_cz": [10.0, 20.0] * kms})
    icrs = table.QTable(
        {"pgc": [2], "ra": [10.0] * deg, "e_ra": [0.0] * deg, "dec": [20.0] * deg, "e_dec": [0.0] * deg}
    )
    return agg, icrs


def _zero_apexes(*names: str) -> dict[str, layer2_import_redshift.Apex]:
    apex = layer2_import_redshift.Apex(lon=0.0, e_lon=0.0, lat=0.0, e_lat=0.0, vel=0.0, e_vel=0.0)
    return dict.fromkeys(names, apex)


def test_velocity_skips_pgc_without_icrs() -> None:
    agg, icrs = _velocity_inputs()
    rows = layer2_import_redshift.build_velocity_rows(agg, icrs, _zero_apexes("heliocentric"))
    assert list(rows["pgc"]) == [2]


def test_velocity_one_row_per_apex() -> None:
    agg, icrs = _velocity_inputs()
    rows = layer2_import_redshift.build_velocity_rows(agg, icrs, _zero_apexes("heliocentric", "local_group", "cmb"))
    assert list(rows["apex"]) == ["heliocentric", "local_group", "cmb"]


def test_velocity_heliocentric_matches_cz() -> None:
    agg, icrs = _velocity_inputs()
    rows = layer2_import_redshift.build_velocity_rows(agg, icrs, _zero_apexes("heliocentric"))
    assert float(rows["v"][0].to_value(u.Unit("km/s"))) == pytest.approx(2000.0)
    assert float(rows["e_v"][0].to_value(u.Unit("km/s"))) == pytest.approx(20.0)

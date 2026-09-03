import datetime

import pytest
import structlog
from astropy import table
from astropy import units as u

from app.lib import mock
from app.tasks import (
    interface,
    layer2_import,
    layer2_import_designation,
    layer2_import_icrs,
    layer2_import_nature,
    layer2_import_redshift,
)


def test_weighted_mean_ra_dec() -> None:
    deg = u.Unit("deg")
    tbl = table.QTable(
        {
            "pgc": [1, 1],
            "ra": [10.0, 20.0] * deg,
            "e_ra": [1.0, 2.0] * deg,
            "dec": [30.0, 40.0] * deg,
            "e_dec": [1.0, 2.0] * deg,
            "datatype": ["regular", "regular"],
        }
    )
    agg = layer2_import_icrs.aggregate_icrs(tbl)
    assert float(agg["ra"][0].to_value(deg)) == pytest.approx(12.0)
    assert float(agg["dec"][0].to_value(deg)) == pytest.approx(32.0)
    formal_err = (1.0 / 1.0**2 + 1.0 / 2.0**2) ** (-0.5)
    assert float(agg["e_ra"][0].to_value(deg)) == pytest.approx(formal_err)
    assert float(agg["e_dec"][0].to_value(deg)) == pytest.approx(formal_err)


def test_ignores_compilations_when_primary_data_exists() -> None:
    deg = u.Unit("deg")
    tbl = table.QTable(
        {
            "pgc": [1, 1, 1],
            "ra": [10.0, 20.0, 100.0] * deg,
            "e_ra": [1.0, 2.0, 0.1] * deg,
            "dec": [30.0, 40.0, 0.0] * deg,
            "e_dec": [1.0, 2.0, 0.1] * deg,
            "datatype": ["regular", "preliminary", "compilation"],
        }
    )
    agg = layer2_import_icrs.aggregate_icrs(tbl)
    assert len(agg) == 1
    assert float(agg["ra"][0].to_value(deg)) == pytest.approx(12.0)
    assert float(agg["dec"][0].to_value(deg)) == pytest.approx(32.0)


def test_aggregates_compilations_when_only_compilations() -> None:
    deg = u.Unit("deg")
    tbl = table.QTable(
        {
            "pgc": [1, 1],
            "ra": [10.0, 20.0] * deg,
            "e_ra": [1.0, 2.0] * deg,
            "dec": [30.0, 40.0] * deg,
            "e_dec": [1.0, 2.0] * deg,
            "datatype": ["compilation", "compilation"],
        }
    )
    agg = layer2_import_icrs.aggregate_icrs(tbl)
    assert len(agg) == 1
    assert float(agg["ra"][0].to_value(deg)) == pytest.approx(12.0)
    assert float(agg["dec"][0].to_value(deg)) == pytest.approx(32.0)


def test_per_pgc_compilation_filtering() -> None:
    deg = u.Unit("deg")
    tbl = table.QTable(
        {
            "pgc": [1, 1, 2, 2],
            "ra": [10.0, 100.0, 10.0, 20.0] * deg,
            "e_ra": [1.0, 0.1, 1.0, 2.0] * deg,
            "dec": [30.0, 0.0, 30.0, 40.0] * deg,
            "e_dec": [1.0, 0.1, 1.0, 2.0] * deg,
            "datatype": ["regular", "compilation", "compilation", "compilation"],
        }
    )
    agg = layer2_import_icrs.aggregate_icrs(tbl)
    by_pgc = {int(pgc): i for i, pgc in enumerate(agg["pgc"])}
    assert float(agg["ra"][by_pgc[1]].to_value(deg)) == pytest.approx(10.0)
    assert float(agg["ra"][by_pgc[2]].to_value(deg)) == pytest.approx(12.0)


def test_weighted_mean_cz() -> None:
    kms = u.Unit("km/s")
    tbl = table.QTable(
        {
            "pgc": [1, 1],
            "cz": [1000.0, 2000.0] * kms,
            "e_cz": [10.0, 20.0] * kms,
            "datatype": ["regular", "regular"],
        }
    )
    agg = layer2_import_redshift.aggregate_redshift(tbl)
    assert float(agg["cz"][0].to_value(kms)) == pytest.approx(1200.0)
    formal_err = (1.0 / 10.0**2 + 1.0 / 20.0**2) ** (-0.5)
    assert float(agg["e_cz"][0].to_value(kms)) == pytest.approx(formal_err)


def test_redshift_ignores_compilations_when_primary_data_exists() -> None:
    kms = u.Unit("km/s")
    tbl = table.QTable(
        {
            "pgc": [1, 1, 1],
            "cz": [1000.0, 2000.0, 5000.0] * kms,
            "e_cz": [10.0, 20.0, 1.0] * kms,
            "datatype": ["regular", "preliminary", "compilation"],
        }
    )
    agg = layer2_import_redshift.aggregate_redshift(tbl)
    assert len(agg) == 1
    assert float(agg["cz"][0].to_value(kms)) == pytest.approx(1200.0)


def test_redshift_aggregates_compilations_when_only_compilations() -> None:
    kms = u.Unit("km/s")
    tbl = table.QTable(
        {
            "pgc": [1, 1],
            "cz": [1000.0, 2000.0] * kms,
            "e_cz": [10.0, 20.0] * kms,
            "datatype": ["compilation", "compilation"],
        }
    )
    agg = layer2_import_redshift.aggregate_redshift(tbl)
    assert len(agg) == 1
    assert float(agg["cz"][0].to_value(kms)) == pytest.approx(1200.0)


def test_redshift_per_pgc_compilation_filtering() -> None:
    kms = u.Unit("km/s")
    tbl = table.QTable(
        {
            "pgc": [1, 1, 2, 2],
            "cz": [1000.0, 5000.0, 1000.0, 2000.0] * kms,
            "e_cz": [10.0, 1.0, 10.0, 20.0] * kms,
            "datatype": ["regular", "compilation", "compilation", "compilation"],
        }
    )
    agg = layer2_import_redshift.aggregate_redshift(tbl)
    by_pgc = {int(pgc): i for i, pgc in enumerate(agg["pgc"])}
    assert float(agg["cz"][by_pgc[1]].to_value(kms)) == pytest.approx(1000.0)
    assert float(agg["cz"][by_pgc[2]].to_value(kms)) == pytest.approx(1200.0)


def test_majority_type_name() -> None:
    tbl = table.QTable(
        {
            "pgc": [1, 1, 1, 2],
            "type_name": ["G", "G", "*", "QSO"],
        }
    )
    agg = layer2_import_nature.aggregate_nature(tbl)
    by_pgc = {int(pgc): str(type_name) for pgc, type_name in zip(agg["pgc"], agg["type_name"], strict=True)}
    assert by_pgc[1] == "G"
    assert by_pgc[2] == "QSO"


def test_majority_design() -> None:
    tbl = table.QTable(
        {
            "pgc": [1, 1, 1, 2],
            "design": ["NGC 224", "NGC 224", "M 31", "NGC 598"],
        }
    )
    agg = layer2_import_designation.aggregate_designation(tbl)
    by_pgc = {int(pgc): str(design) for pgc, design in zip(agg["pgc"], agg["design"], strict=True)}
    assert by_pgc[1] == "NGC 224"
    assert by_pgc[2] == "NGC 598"


def test_parse_since_none() -> None:
    assert interface.parse_since(None) is None


def test_datetime_adds_utc_if_naive() -> None:
    dt = datetime.datetime(2020, 1, 2, 3, 4, 5)  # noqa: DTZ001
    got = interface.parse_since(dt)
    assert got == datetime.datetime(2020, 1, 2, 3, 4, 5, tzinfo=datetime.UTC)


def test_datetime_keeps_timezone() -> None:
    dt = datetime.datetime(2020, 1, 2, 3, 4, 5, tzinfo=datetime.UTC)
    assert interface.parse_since(dt) is dt


def test_isoformat_string() -> None:
    got = interface.parse_since("2020-01-02T03:04:05Z")
    assert got == datetime.datetime(2020, 1, 2, 3, 4, 5, tzinfo=datetime.UTC)


def test_default_catalogs() -> None:
    task = layer2_import.Layer2ImportTask(structlog.get_logger())
    assert task.catalogs == list(layer2_import.DEFAULT_CATALOGS)


def test_custom_catalogs() -> None:
    task = layer2_import.Layer2ImportTask(structlog.get_logger(), catalogs=["icrs", "nature"])
    assert task.catalogs == ["icrs", "nature"]


def test_unknown_catalog_raises() -> None:
    with pytest.raises(ValueError):
        layer2_import.Layer2ImportTask(structlog.get_logger(), catalogs=["icrs", "nope"])


def test_run_passes_params_to_selected_catalogs() -> None:
    since = datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)
    task = layer2_import.Layer2ImportTask(
        structlog.get_logger(),
        batch_size=10,
        dry_run=True,
        since=since,
        cleanup_orphans=False,
        catalogs=["designation"],
    )
    task.pg_storage = mock.Mock()
    task.repository = mock.Mock()

    designation_cls = mock.Mock()
    child = mock.Mock()
    designation_cls.return_value = child
    with mock.patch.dict(layer2_import.CATALOG_TASKS, {"designation": designation_cls}):
        task.run()

    designation_cls.assert_called_once_with(
        logger=task.log,
        batch_size=10,
        dry_run=True,
        silent=False,
        since=since,
        cleanup_orphans=False,
    )
    child.run.assert_called_once_with()

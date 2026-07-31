import datetime
import unittest
from unittest import mock

import structlog
from astropy import table
from astropy import units as u

from app.tasks import (
    interface,
    layer2_import,
    layer2_import_designation,
    layer2_import_icrs,
    layer2_import_nature,
    layer2_import_redshift,
)


class AggregateIcrsTest(unittest.TestCase):
    def test_weighted_mean_ra_dec(self) -> None:
        deg = u.Unit("deg")
        tbl = table.QTable(
            {
                "pgc": [1, 1],
                "ra": [10.0, 20.0] * deg,
                "e_ra": [1.0, 2.0] * deg,
                "dec": [30.0, 40.0] * deg,
                "e_dec": [1.0, 2.0] * deg,
            }
        )
        agg = layer2_import_icrs.aggregate_icrs(tbl)
        self.assertAlmostEqual(float(agg["ra"][0].to_value(deg)), 12.0)
        self.assertAlmostEqual(float(agg["dec"][0].to_value(deg)), 32.0)
        formal_err = (1.0 / 1.0**2 + 1.0 / 2.0**2) ** (-0.5)
        self.assertAlmostEqual(float(agg["e_ra"][0].to_value(deg)), formal_err)
        self.assertAlmostEqual(float(agg["e_dec"][0].to_value(deg)), formal_err)


class AggregateRedshiftTest(unittest.TestCase):
    def test_weighted_mean_cz(self) -> None:
        kms = u.Unit("km/s")
        tbl = table.QTable(
            {
                "pgc": [1, 1],
                "cz": [1000.0, 2000.0] * kms,
                "e_cz": [10.0, 20.0] * kms,
            }
        )
        agg = layer2_import_redshift.aggregate_redshift(tbl)
        self.assertAlmostEqual(float(agg["cz"][0].to_value(kms)), 1200.0)
        formal_err = (1.0 / 10.0**2 + 1.0 / 20.0**2) ** (-0.5)
        self.assertAlmostEqual(float(agg["e_cz"][0].to_value(kms)), formal_err)


class AggregateNatureTest(unittest.TestCase):
    def test_majority_type_name(self) -> None:
        tbl = table.QTable(
            {
                "pgc": [1, 1, 1, 2],
                "type_name": ["G", "G", "*", "QSO"],
            }
        )
        agg = layer2_import_nature.aggregate_nature(tbl)
        by_pgc = {int(pgc): str(type_name) for pgc, type_name in zip(agg["pgc"], agg["type_name"], strict=True)}
        self.assertEqual(by_pgc[1], "G")
        self.assertEqual(by_pgc[2], "QSO")


class AggregateDesignationTest(unittest.TestCase):
    def test_majority_design(self) -> None:
        tbl = table.QTable(
            {
                "pgc": [1, 1, 1, 2],
                "design": ["NGC 224", "NGC 224", "M 31", "NGC 598"],
            }
        )
        agg = layer2_import_designation.aggregate_designation(tbl)
        by_pgc = {int(pgc): str(design) for pgc, design in zip(agg["pgc"], agg["design"], strict=True)}
        self.assertEqual(by_pgc[1], "NGC 224")
        self.assertEqual(by_pgc[2], "NGC 598")


class ParseSinceTest(unittest.TestCase):
    def test_none(self) -> None:
        self.assertIsNone(interface.parse_since(None))

    def test_datetime_adds_utc_if_naive(self) -> None:
        dt = datetime.datetime(2020, 1, 2, 3, 4, 5)  # noqa: DTZ001
        got = interface.parse_since(dt)
        self.assertEqual(got, datetime.datetime(2020, 1, 2, 3, 4, 5, tzinfo=datetime.UTC))

    def test_datetime_keeps_timezone(self) -> None:
        dt = datetime.datetime(2020, 1, 2, 3, 4, 5, tzinfo=datetime.UTC)
        self.assertIs(interface.parse_since(dt), dt)

    def test_isoformat_string(self) -> None:
        got = interface.parse_since("2020-01-02T03:04:05Z")
        self.assertEqual(got, datetime.datetime(2020, 1, 2, 3, 4, 5, tzinfo=datetime.UTC))


class Layer2ImportTaskParamsTest(unittest.TestCase):
    def test_default_catalogs(self) -> None:
        task = layer2_import.Layer2ImportTask(structlog.get_logger())
        self.assertEqual(task.catalogs, list(layer2_import.DEFAULT_CATALOGS))

    def test_custom_catalogs(self) -> None:
        task = layer2_import.Layer2ImportTask(structlog.get_logger(), catalogs=["icrs", "nature"])
        self.assertEqual(task.catalogs, ["icrs", "nature"])

    def test_unknown_catalog_raises(self) -> None:
        with self.assertRaises(ValueError):
            layer2_import.Layer2ImportTask(structlog.get_logger(), catalogs=["icrs", "nope"])

    def test_run_passes_params_to_selected_catalogs(self) -> None:
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
        task.layer1_repository = mock.Mock()
        task.layer2_repository = mock.Mock()

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

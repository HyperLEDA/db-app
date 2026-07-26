import datetime
import unittest
from unittest import mock

import structlog

from app.tasks import interface, layer2_import


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

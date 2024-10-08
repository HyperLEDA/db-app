import unittest
from unittest import mock

import numpy as np
import structlog
from astropy import table

from app.domain import tasks
from app.lib import testing


class DownloadVizierTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = testing.get_test_postgres_storage()

    def tearDown(self):
        self.storage.clear()

    @mock.patch("astroquery.vizier.VizierClass")
    def test_table_downloading_simple(self, vizier_mock):
        test_table = table.Table(
            names=("name", "ra", "dec"),
            dtype=("str", "f4", "f4"),
            descriptions=("test name descr", "test ra descr", "test dec descr"),
        )
        test_table.meta = {"name": "test_table", "description": "test descr"}
        test_table.add_row(("D333", 120.0, 10))
        test_table.add_row(("D541", 90, -50))

        testing.returns(vizier_mock.return_value.get_catalogs, [test_table])

        tasks.download_vizier_table(
            self.storage.get_storage(),
            tasks.DownloadVizierTableParams("test_catalog", "test_table"),
            structlog.get_logger(),
        )
        rows = self.storage.get_storage().query("SELECT name, ra, dec FROM rawdata.data_vizier_test_table")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], "D333")
        self.assertEqual(rows[1]["name"], "D541")

        comment_rows = self.storage.get_storage().query(
            "SELECT param FROM meta.table_info WHERE schema_name = 'rawdata' AND table_name = 'data_vizier_test_table'"
        )
        self.assertDictEqual(comment_rows[0]["param"], {"description": "test descr", "name_col": None})

        comment_rows = self.storage.get_storage().query("""
            SELECT param
            FROM meta.column_info
            WHERE schema_name = 'rawdata'
                AND table_name = 'data_vizier_test_table'
                AND column_name = 'name'
            """)
        self.assertDictEqual(comment_rows[0]["param"], {"data_type": "text", "description": "test name descr"})
        comment_rows = self.storage.get_storage().query("""
            SELECT param
            FROM meta.column_info
            WHERE schema_name = 'rawdata'
                AND table_name = 'data_vizier_test_table'
                AND column_name = 'ra'
            """)
        self.assertDictEqual(
            comment_rows[0]["param"], {"data_type": "double precision", "description": "test ra descr"}
        )
        comment_rows = self.storage.get_storage().query("""
            SELECT param
            FROM meta.column_info
            WHERE schema_name = 'rawdata'
                AND table_name = 'data_vizier_test_table'
                AND column_name = 'dec'
            """)
        self.assertDictEqual(
            comment_rows[0]["param"], {"data_type": "double precision", "description": "test dec descr"}
        )

    @mock.patch("astroquery.vizier.VizierClass")
    def test_bad_column_names(self, vizier_mock):
        test_table = table.Table(names=("name", "object-type"), dtype=("str", "str"))
        test_table.meta = {"name": "test_table"}
        test_table.add_row(("M333", "type1"))
        test_table.add_row(("M541", "type2"))

        testing.returns(vizier_mock.return_value.get_catalogs, [test_table])

        tasks.download_vizier_table(
            self.storage.get_storage(),
            tasks.DownloadVizierTableParams("test_catalog", "test_table"),
            structlog.get_logger(),
        )
        rows = self.storage.get_storage().query("SELECT name, object_type FROM rawdata.data_vizier_test_table")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["object_type"], "type1")
        self.assertEqual(rows[1]["object_type"], "type2")

    @mock.patch("astroquery.vizier.VizierClass")
    def test_nans_in_data(self, vizier_mock):
        test_table = table.Table(names=("name", "ra", "dec"), dtype=("str", "f4", "f4"))
        test_table.meta = {"name": "test_table"}
        test_table.add_row(("M333", np.nan, 10))
        test_table.add_row(("M541", 90, -50))

        testing.returns(vizier_mock.return_value.get_catalogs, [test_table])

        tasks.download_vizier_table(
            self.storage.get_storage(),
            tasks.DownloadVizierTableParams("test_catalog", "test_table"),
            structlog.get_logger(),
        )
        rows = self.storage.get_storage().query("SELECT name, ra, dec FROM rawdata.data_vizier_test_table")
        self.assertEqual(len(rows), 2)
        self.assertTrue(np.isnan(rows[0]["ra"]))

    @mock.patch("astroquery.vizier.VizierClass")
    def test_caching_table(self, vizier_mock):
        test_table = table.Table(names=("name", "ra", "dec"), dtype=("str", "f4", "f4"))
        test_table.meta = {"name": "test_table"}
        test_table.add_row(("M333", np.nan, 10))
        test_table.add_row(("M541", 90, -50))

        testing.returns(vizier_mock.return_value.get_catalogs, [test_table])

        tasks.download_vizier_table(
            self.storage.get_storage(),
            tasks.DownloadVizierTableParams("test_catalog", "test_table"),
            structlog.get_logger(),
        )

        tasks.download_vizier_table(
            self.storage.get_storage(),
            tasks.DownloadVizierTableParams("test_catalog", "test_table"),
            structlog.get_logger(),
        )

        vizier_mock.return_value.get_catalogs.assert_called_once()
        rows = self.storage.get_storage().query("SELECT * FROM rawdata.data_vizier_test_table")
        self.assertEqual(len(rows), 2)

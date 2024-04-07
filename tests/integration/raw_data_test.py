import unittest
from unittest import mock

import numpy as np
import structlog
from astropy import table
from astroquery import vizier

from app.data import repositories
from app.domain import model, usecases
from app.lib import testing


class RawDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = testing.TestPostgresStorage("postgres/migrations")
        cls.storage.start()

        common_repo = repositories.CommonRepository(cls.storage.get_storage(), structlog.get_logger())
        layer0_repo = repositories.Layer0Repository(cls.storage.get_storage(), structlog.get_logger())
        layer1_repo = repositories.Layer1Repository(cls.storage.get_storage(), structlog.get_logger())
        cls.actions = usecases.Actions(common_repo, layer0_repo, layer1_repo, None, structlog.get_logger())

    @classmethod
    def tearDownClass(cls):
        cls.storage.stop()

    def tearDown(self):
        self.storage.clear()

    def test_table_downloading_simple(self):
        test_table = table.Table(names=("name", "ra", "dec"), dtype=("S2", "f4", "f4"))
        test_table.meta = {"name": "test_table"}
        test_table.add_row(("M333", 120.0, 10))
        test_table.add_row(("M541", 90, -50))

        vizier.Vizier.get_catalogs = mock.MagicMock(return_value=[test_table])

        response = self.actions.choose_table(model.ChooseTableRequest("test_catalog", "test_table"))
        rows = self.storage.get_storage().query(f"SELECT name, ra, dec FROM rawdata.data_{response.id}", [])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], "M333")
        self.assertEqual(rows[1]["name"], "M541")

    def test_bad_column_names(self):
        test_table = table.Table(names=("name", "object-type"), dtype=("S2", "S2"))
        test_table.meta = {"name": "test_table"}
        test_table.add_row(("M333", "type1"))
        test_table.add_row(("M541", "type2"))

        vizier.Vizier.get_catalogs = mock.MagicMock(return_value=[test_table])

        response = self.actions.choose_table(model.ChooseTableRequest("test_catalog", "test_table"))
        rows = self.storage.get_storage().query(f"SELECT name, object_type FROM rawdata.data_{response.id}", [])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["object_type"], "type1")
        self.assertEqual(rows[1]["object_type"], "type2")

    def test_nans_in_data(self):
        test_table = table.Table(names=("name", "ra", "dec"), dtype=("S2", "f4", "f4"))
        test_table.meta = {"name": "test_table"}
        test_table.add_row(("M333", np.NaN, 10))
        test_table.add_row(("M541", 90, -50))

        vizier.Vizier.get_catalogs = mock.MagicMock(return_value=[test_table])

        response = self.actions.choose_table(model.ChooseTableRequest("test_catalog", "test_table"))
        rows = self.storage.get_storage().query(f"SELECT name, ra, dec FROM rawdata.data_{response.id}", [])
        self.assertEqual(len(rows), 2)
        self.assertTrue(np.isnan(rows[0]["ra"]))

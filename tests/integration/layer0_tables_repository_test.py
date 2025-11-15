import unittest

import numpy as np
import pandas as pd
import structlog
from astropy import units as u

from app.data import model, repositories
from app.data.repositories.layer0 import tables
from tests import lib


class LayerTables0RepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()
        cls.common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer0_repo = tables.Layer0TableRepository(cls.pg_storage.get_storage())

        cls.bib_id = cls.common_repo.create_bibliography("123456", 2000, ["test"], "test")

    def tearDown(self):
        self.pg_storage.clear()

    def test_write_and_fetch_table(self):
        table_meta = model.Layer0TableMeta(
            "test_table",
            [
                model.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit=u.Unit("hour")),
                model.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit=u.Unit("hour")),
            ],
            self.bib_id,
        )

        _ = self.layer0_repo.create_table(table_meta)
        test_data = pd.DataFrame({"ra": [12.1, 11.1], "dec": [1.0, 2.0]})
        raw_data = model.Layer0RawData(table_meta.table_name, test_data)

        self.layer0_repo.insert_raw_data(raw_data)

        fetched_data = self.layer0_repo.fetch_table(table_meta.table_name)

        self.assertEqual(len(fetched_data), 2)
        self.assertEqual(list(fetched_data.columns), ["ra", "dec"])

        np.testing.assert_array_equal(fetched_data["ra"], test_data["ra"])
        self.assertEqual(fetched_data["ra"].unit, u.Unit("hour"))  # type: ignore
        np.testing.assert_array_equal(fetched_data["dec"], test_data["dec"])

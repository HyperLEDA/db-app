import unittest

import numpy as np
import pandas as pd
import structlog
from astropy import units as u

from app.adminapi import model, repository
from app.lib.storage import enums, postgres
from tests import lib


class LayerTables0RepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get(enums.PG_ENUM_REGISTRY)
        cls.repo = repository.Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.bib_id = cls.repo.create_bibliography("123456", 2000, ["test"], "test")

    def tearDown(self):
        self.pg_storage.clear()

    def test_write_and_fetch_table(self):
        table_meta = model.Layer0TableMeta(
            postgres.TableInfo(
                schema=repository.RAWDATA_SCHEMA,
                name="test_table",
                columns={
                    "ra": postgres.ColumnInfo("ra", "float", ucd="pos.eq.ra", unit="hour"),
                    "dec": postgres.ColumnInfo("dec", "float", ucd="pos.eq.dec", unit="hour"),
                },
            ),
            self.bib_id,
        )

        _ = self.repo.create_table(table_meta)
        test_data = pd.DataFrame({"ra": [12.1, 11.1], "dec": [1.0, 2.0]})
        raw_data = model.Layer0RawData(table_meta.table_info.name, test_data)

        self.repo.insert_raw_data(raw_data)

        fetched_data = self.repo.fetch_table(table_meta.table_info.name)

        self.assertEqual(len(fetched_data), 2)
        self.assertEqual(list(fetched_data.columns), ["ra", "dec"])

        np.testing.assert_array_equal(fetched_data["ra"], test_data["ra"])
        self.assertEqual(fetched_data["ra"].unit, u.Unit("hour"))
        np.testing.assert_array_equal(fetched_data["dec"], test_data["dec"])

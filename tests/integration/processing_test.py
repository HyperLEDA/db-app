import unittest

import pandas
import structlog
from astropy import units as u

from app import entities
from app.data import model, repositories
from app.domain import processing
from app.lib.storage import enums
from tests import lib


class MarkObjectsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()

        cls.common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())

    def tearDown(self):
        self.pg_storage.clear()

    def test_one_batch(self):
        bib_id = self.common_repo.create_bibliography("123456", 2000, ["test"], "test")
        table_resp = self.layer0_repo.create_table(
            entities.Layer0Creation(
                "test_table",
                [
                    entities.ColumnDescription(repositories.INTERNAL_ID_COLUMN_NAME, "text"),
                    entities.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit=u.deg),
                    entities.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit=u.deg),
                ],
                bib_id,
                enums.DataType.REGULAR,
            )
        )

        data = pandas.DataFrame(
            {
                repositories.INTERNAL_ID_COLUMN_NAME: ["1", "2", "3"],
                "ra": [10.0, 20.0, 30.0],
                "dec": [20.0, 30.0, 40.0],
            }
        )

        self.layer0_repo.insert_raw_data(model.Layer0RawData(table_resp.table_id, data))

        processing.mark_objects(self.layer0_repo, table_resp.table_id, 5)

        actual = self.layer0_repo.get_objects(table_resp.table_id, 5, 0)
        self.assertEqual(len(actual), 3)

    def test_multiple_batches(self):
        pass

    def test_number_of_objects_divisible_by_batch_size(self):
        pass

    def test_table_patched_after_processing(self):
        pass

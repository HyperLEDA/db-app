import datetime
import unittest

import pandas
import structlog
from astropy import units as u

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

    def _get_table(self) -> int:
        bib_id = self.common_repo.create_bibliography("123456", 2000, ["test"], "test")
        table_resp = self.layer0_repo.create_table(
            model.Layer0TableMeta(
                "test_table",
                [
                    model.ColumnDescription(repositories.INTERNAL_ID_COLUMN_NAME, "text"),
                    model.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit=u.deg),
                    model.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit=u.deg),
                    model.ColumnDescription("redshift", "float", unit=u.dimensionless_unscaled),
                ],
                bib_id,
                enums.DataType.REGULAR,
            )
        )

        data = pandas.DataFrame(
            {
                repositories.INTERNAL_ID_COLUMN_NAME: ["1", "2", "3", "4", "5", "6"],
                "ra": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
                "dec": [20.0, 30.0, 40.0, 50.0, 60.0, 70.0],
                "redshift": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            }
        )

        self.layer0_repo.insert_raw_data(model.Layer0RawData(table_resp.table_id, data))

        return table_resp.table_id

    def test_multiple_batches(self):
        table_id = self._get_table()

        processing.mark_objects(self.layer0_repo, table_id, 5)

        actual = self.layer0_repo.get_objects(table_id, 5, 0)
        self.assertEqual(len(actual), 5)

        actual = self.layer0_repo.get_objects(table_id, 5, 5)
        self.assertEqual(len(actual), 1)

    def test_number_of_objects_divisible_by_batch_size(self):
        table_id = self._get_table()

        processing.mark_objects(self.layer0_repo, table_id, 3)

        actual = self.layer0_repo.get_objects(table_id, 3, 0)
        self.assertEqual(len(actual), 3)

        actual = self.layer0_repo.get_objects(table_id, 3, 3)
        self.assertEqual(len(actual), 3)

    def test_table_patched_after_processing(self):
        table_id = self._get_table()

        processing.mark_objects(self.layer0_repo, table_id, 5)

        before = self.layer0_repo.get_objects(table_id, 5, 0)
        obj_before = before[0]

        self.layer0_repo.update_column_metadata(
            table_id,
            model.ColumnDescription("redshift", "float", ucd="src.redshift"),
        )

        processing.mark_objects(self.layer0_repo, table_id, 5)

        after = self.layer0_repo.get_objects(table_id, 5, 0)
        obj_after = after[0]

        self.assertGreater(len(obj_after.data), len(obj_before.data))

    def test_table_didnt_change_since_last_upload(self):
        table_id = self._get_table()

        processing.mark_objects(self.layer0_repo, table_id, 5)
        modification_dt = datetime.datetime.now(tz=datetime.UTC)

        processing.mark_objects(self.layer0_repo, table_id, 5)

        stats = self.layer0_repo.get_table_statistics(table_id)
        self.assertLess(stats.last_modified_dt.timestamp(), modification_dt.timestamp())

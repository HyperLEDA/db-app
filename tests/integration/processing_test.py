import datetime
import unittest
import uuid

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

    def _get_table(self) -> tuple[int, str]:
        self.layer0_repo.add_homogenization_rules(
            [
                model.HomogenizationRule(model.RawCatalog.ICRS.value, "ra", {"column_name": "ra"}),
                model.HomogenizationRule(model.RawCatalog.ICRS.value, "dec", {"column_name": "dec"}),
                model.HomogenizationRule(model.RawCatalog.ICRS.value, "e_ra", {"column_name": "e_ra"}),
                model.HomogenizationRule(model.RawCatalog.ICRS.value, "e_dec", {"column_name": "e_dec"}),
                model.HomogenizationRule(model.RawCatalog.REDSHIFT.value, "cz", {"column_name": "redshift"}),
                model.HomogenizationRule(model.RawCatalog.REDSHIFT.value, "e_cz", {"column_name": "e_redshift"}),
            ]
        )

        table_name = "test_table"
        bib_id = self.common_repo.create_bibliography("123456", 2000, ["test"], "test")
        table_resp = self.layer0_repo.create_table(
            model.Layer0TableMeta(
                table_name,
                [
                    model.ColumnDescription(repositories.INTERNAL_ID_COLUMN_NAME, "text"),
                    model.ColumnDescription("ra", "float", unit=u.Unit("deg")),
                    model.ColumnDescription("dec", "float", unit=u.Unit("deg")),
                    model.ColumnDescription("e_ra", "float", unit=u.Unit("deg")),
                    model.ColumnDescription("e_dec", "float", unit=u.Unit("deg")),
                    model.ColumnDescription("redshift", "float", unit=u.dimensionless_unscaled),
                    model.ColumnDescription("e_redshift", "float"),
                ],
                bib_id,
                enums.DataType.REGULAR,
            )
        )

        data = pandas.DataFrame(
            {
                repositories.INTERNAL_ID_COLUMN_NAME: [
                    str(uuid.uuid4()),
                    str(uuid.uuid4()),
                    str(uuid.uuid4()),
                    str(uuid.uuid4()),
                    str(uuid.uuid4()),
                    str(uuid.uuid4()),
                ],
                "ra": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
                "dec": [20.0, 30.0, 40.0, 50.0, 60.0, 70.0],
                "e_ra": [0.1] * 6,
                "e_dec": [0.11] * 6,
                "redshift": [100, 200, 300, 400, 500, 600],
                "e_redshift": [2] * 6,
            }
        )

        self.layer0_repo.insert_raw_data(model.Layer0RawData(table_resp.table_id, data))
        self.layer0_repo.add_modifier("test_table", [model.Modifier("redshift", "add_unit", {"unit": "km/s"})])

        return table_resp.table_id, table_name

    def test_multiple_batches(self):
        table_id, table_name = self._get_table()

        processing.mark_objects(self.layer0_repo, table_id, 5)

        actual = self.layer0_repo.get_objects(5, table_id=table_id)
        self.assertEqual(len(actual), 5)

        actual = self.layer0_repo.get_objects(5, offset=actual[-1].object_id, table_id=table_id)
        self.assertEqual(len(actual), 1)

    def test_number_of_objects_divisible_by_batch_size(self):
        table_id, table_name = self._get_table()

        processing.mark_objects(self.layer0_repo, table_id, 3)

        actual = self.layer0_repo.get_objects(3, table_id=table_id)
        self.assertEqual(len(actual), 3)

        actual = self.layer0_repo.get_objects(3, offset=actual[-1].object_id, table_id=table_id)
        self.assertEqual(len(actual), 3)

    def test_table_patched_after_processing(self):
        table_id, table_name = self._get_table()

        processing.mark_objects(self.layer0_repo, table_id, 5)

        before = self.layer0_repo.get_objects(5, table_id=table_id)
        obj_before = before[0]

        self.layer0_repo.update_column_metadata(
            table_name,
            model.ColumnDescription("e_redshift", "float", unit=u.Unit("km/s")),
        )

        processing.mark_objects(self.layer0_repo, table_id, 5)

        after = self.layer0_repo.get_objects(5, table_id=table_id)
        obj_after = after[0]

        self.assertGreater(len(obj_after.data), len(obj_before.data))

    def test_table_didnt_change_since_last_upload(self):
        table_id, table_name = self._get_table()

        processing.mark_objects(self.layer0_repo, table_id, 5)
        modification_dt = datetime.datetime.now(tz=datetime.UTC)

        processing.mark_objects(self.layer0_repo, table_id, 5)

        stats = self.layer0_repo.get_table_statistics(table_id)
        self.assertLess(stats.last_modified_dt.timestamp(), modification_dt.timestamp())

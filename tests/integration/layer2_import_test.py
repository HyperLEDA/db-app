import unittest

import structlog

from app import tasks
from app.data import model, repositories
from app.data.repositories import layer2
from app.tasks import layer2_import
from tests import lib


class Layer2ImportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pg_storage = lib.TestPostgresStorage.get()

        cls.common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer1_repo = repositories.Layer1Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer2_repo = repositories.Layer2Repository(cls.pg_storage.get_storage(), structlog.get_logger())

        cls.task = layer2_import.Layer2ImportTask()
        cls.task.prepare(tasks.Config(cls.pg_storage.config))

    def tearDown(self):
        self.pg_storage.clear()

    @classmethod
    def tearDownClass(cls):
        cls.task.cleanup()

    def _get_table(self, table_name: str) -> int:
        bib_id = self.common_repo.create_bibliography("123456", 2000, ["test"], "test")
        table_resp = self.layer0_repo.create_table(model.Layer0TableMeta(table_name, [], bib_id))

        return table_resp.table_id

    def test_import_two_catalogs(self):
        table_id = self._get_table("test_import_two_catalogs")
        self.layer0_repo.upsert_objects(
            table_id,
            [model.Layer0Object("123", []), model.Layer0Object("124", [])],
        )

        self.layer0_repo.upsert_pgc({"123": 1234, "124": 1245})
        self.layer1_repo.save_data(
            [
                model.Layer1Observation("123", model.ICRSCatalogObject(12, 0.2, 13, 0.2)),
                model.Layer1Observation("124", model.ICRSCatalogObject(14, 0.2, 15, 0.2)),
                model.Layer1Observation("123", model.DesignationCatalogObject("test1")),
                model.Layer1Observation("124", model.DesignationCatalogObject("test2")),
            ]
        )

        self.task.run()

        actual = self.layer2_repo.query(
            [model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION],
            layer2.PGCOneOfFilter([1234]),
            layer2.CombinedSearchParams([]),
            10,
            0,
        )
        expected = model.Layer2Object(
            1234, [model.ICRSCatalogObject(12, 0.2, 13, 0.2), model.DesignationCatalogObject("test1")]
        )

        self.assertEqual(actual, [expected])

    def test_updated_objects(self):
        self.test_import_two_catalogs()
        table_id = self._get_table("test_updated_objects")
        self.layer0_repo.upsert_objects(
            table_id,
            [model.Layer0Object("125", []), model.Layer0Object("126", [])],
        )
        self.layer0_repo.upsert_pgc({"125": 1234, "126": 1234})

        last_update_dt = self.layer2_repo.get_last_update_time()

        self.layer1_repo.save_data(
            [
                model.Layer1Observation("125", model.DesignationCatalogObject("test3")),
                model.Layer1Observation("126", model.DesignationCatalogObject("test3")),
            ]
        )

        self.task.run()

        new_last_update_dt = self.layer2_repo.get_last_update_time()
        self.assertGreater(new_last_update_dt, last_update_dt)

        actual = self.layer2_repo.query(
            [model.RawCatalog.DESIGNATION],
            layer2.PGCOneOfFilter([1234]),
            layer2.CombinedSearchParams([]),
            10,
            0,
        )
        expected = model.DesignationCatalogObject("test3")
        self.assertEqual(len(actual), 1)
        self.assertEqual(len(actual[0].data), 1)
        self.assertEqual(actual[0].data[0], expected)

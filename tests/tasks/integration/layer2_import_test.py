import unittest

import structlog

from app import tasks
from app.data import model, repositories
from app.lib.storage import enums
from app.tasks import layer2_import, repository
from tests import lib


class Layer2ImportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pg_storage = lib.TestPostgresStorage.get(enums.PG_ENUM_REGISTRY)

        cls.common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer1_repo = repositories.Layer1Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.repo = repository.Repository(cls.pg_storage.get_storage(), structlog.get_logger())

        cls.task = layer2_import.Layer2ImportTask(structlog.get_logger())
        cls.task.prepare(tasks.Config(storage=cls.pg_storage.config))

    def tearDown(self):
        self.pg_storage.clear()

    @classmethod
    def tearDownClass(cls):
        cls.task.cleanup()

    def _get_table(self, table_name: str) -> int:
        bib_id = self.common_repo.create_bibliography("123456", 2000, ["test"], "test")
        table_resp = self.layer0_repo.create_table(model.Layer0TableMeta(table_name, [], bib_id))

        return table_resp.table_id

    def _designation(self, pgc: int) -> model.DesignationCatalogObject | None:
        rows = self.pg_storage.get_storage().query(
            "SELECT design FROM layer2.designation WHERE pgc = %s",
            params=[pgc],
        )
        if not rows:
            return None
        return model.DesignationCatalogObject(design=rows[0]["design"])

    def _icrs(self, pgc: int) -> model.ICRSCatalogObject | None:
        rows = self.pg_storage.get_storage().query(
            "SELECT ra, e_ra, dec, e_dec FROM layer2.icrs WHERE pgc = %s",
            params=[pgc],
        )
        if not rows:
            return None
        row = rows[0]
        return model.ICRSCatalogObject(ra=row["ra"], e_ra=row["e_ra"], dec=row["dec"], e_dec=row["e_dec"])

    def test_import_two_catalogs(self):
        _ = self._get_table("test_import_two_catalogs")
        self.layer0_repo.register_records(
            "test_import_two_catalogs",
            ["123", "124"],
        )

        self.common_repo.register_pgcs([1234, 1245])
        self.layer0_repo.upsert_pgc({"123": 1234, "124": 1245})
        self.layer1_repo.save_structured_data(
            "icrs.data", ["ra", "e_ra", "dec", "e_dec"], ["123", "124"], [[12, 0.2, 13, 0.2], [14, 0.2, 15, 0.2]]
        )
        self.layer1_repo.save_structured_data(
            "designation.data",
            ["design"],
            ["123", "124"],
            [["test1"], ["test2"]],
            conflict_keys=model.DesignationCatalogObject.layer1_primary_keys(),
        )

        self.task.run()

        icrs = self._icrs(1234)
        designation = self._designation(1234)
        self.assertIsNotNone(icrs)
        self.assertIsNotNone(designation)
        assert icrs is not None
        assert designation is not None
        lib.assert_catalog_object_equal(self, icrs, model.ICRSCatalogObject(ra=12, e_ra=0.2, dec=13, e_dec=0.2))
        lib.assert_catalog_object_equal(self, designation, model.DesignationCatalogObject("test1"))

    def test_updated_objects(self):
        self.test_import_two_catalogs()
        _ = self._get_table("test_updated_objects")
        self.layer0_repo.register_records(
            "test_updated_objects",
            ["125", "126"],
        )
        self.layer0_repo.upsert_pgc({"125": 1234, "126": 1234})

        last_update_dt = self.repo.get_last_update_time(model.RawCatalog.DESIGNATION)

        self.layer1_repo.save_structured_data(
            "designation.data",
            ["design"],
            ["125", "126"],
            [["test3"], ["test3"]],
            conflict_keys=model.DesignationCatalogObject.layer1_primary_keys(),
        )

        self.task.run()

        new_last_update_dt = self.repo.get_last_update_time(model.RawCatalog.DESIGNATION)
        self.assertGreater(new_last_update_dt, last_update_dt)

        designation = self._designation(1234)
        self.assertIsNotNone(designation)
        assert designation is not None
        lib.assert_catalog_object_equal(self, designation, model.DesignationCatalogObject("test3"))

    def test_layer1_only_update_recalculates_layer2(self) -> None:
        self.test_import_two_catalogs()

        last_update_dt = self.repo.get_last_update_time(model.RawCatalog.ICRS)

        self.layer1_repo.save_structured_data(
            "icrs.data",
            ["ra", "e_ra", "dec", "e_dec"],
            ["123"],
            [[22.0, 0.2, 23.0, 0.2]],
        )

        self.task.run()

        new_last_update_dt = self.repo.get_last_update_time(model.RawCatalog.ICRS)
        self.assertGreater(new_last_update_dt, last_update_dt)

        icrs = self._icrs(1234)
        self.assertIsNotNone(icrs)
        assert icrs is not None
        lib.assert_catalog_object_equal(self, icrs, model.ICRSCatalogObject(ra=22.0, e_ra=0.2, dec=23.0, e_dec=0.2))

import unittest

import structlog

from app import tasks
from app.data import model
from app.lib.storage import enums
from app.tasks import layer2_import, repository
from tests import lib
from tests.lib import layer_seed


class Layer2ImportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pg_storage = lib.TestPostgresStorage.get(enums.PG_ENUM_REGISTRY)
        cls.storage = cls.pg_storage.get_storage()
        cls.repo = repository.Repository(cls.storage, structlog.get_logger())
        cls.task = layer2_import.Layer2ImportTask(structlog.get_logger())
        cls.task.prepare(tasks.Config(storage=cls.pg_storage.config))

    def tearDown(self):
        self.pg_storage.clear()

    @classmethod
    def tearDownClass(cls):
        cls.task.cleanup()

    def _get_table(self, table_name: str) -> int:
        bib_id = layer_seed.create_bibliography(self.storage, "123456", 2000, ["test"], "test")
        return layer_seed.create_table(self.storage, table_name, bib_id)

    def _designation(self, pgc: int) -> model.DesignationCatalogObject | None:
        rows = self.storage.query(
            "SELECT design FROM layer2.designation WHERE pgc = %s",
            params=[pgc],
        )
        if not rows:
            return None
        return model.DesignationCatalogObject(design=rows[0]["design"])

    def _icrs(self, pgc: int) -> model.ICRSCatalogObject | None:
        rows = self.storage.query(
            "SELECT ra, e_ra, dec, e_dec FROM layer2.icrs WHERE pgc = %s",
            params=[pgc],
        )
        if not rows:
            return None
        row = rows[0]
        return model.ICRSCatalogObject(ra=row["ra"], e_ra=row["e_ra"], dec=row["dec"], e_dec=row["e_dec"])

    def test_import_two_catalogs(self):
        _ = self._get_table("test_import_two_catalogs")
        layer_seed.register_records(
            self.storage,
            "test_import_two_catalogs",
            ["123", "124"],
        )
        layer_seed.register_pgcs(self.storage, [1234, 1245])
        layer_seed.upsert_pgc(self.storage, {"123": 1234, "124": 1245})
        layer_seed.save_structured_data(
            self.storage,
            "icrs.data",
            ["ra", "e_ra", "dec", "e_dec"],
            ["123", "124"],
            [[12, 0.2, 13, 0.2], [14, 0.2, 15, 0.2]],
        )
        layer_seed.save_structured_data(
            self.storage,
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
        layer_seed.register_records(
            self.storage,
            "test_updated_objects",
            ["125", "126"],
        )
        layer_seed.upsert_pgc(self.storage, {"125": 1234, "126": 1234})

        last_update_dt = self.repo.get_last_update_time(model.RawCatalog.DESIGNATION)

        layer_seed.save_structured_data(
            self.storage,
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

        layer_seed.save_structured_data(
            self.storage,
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

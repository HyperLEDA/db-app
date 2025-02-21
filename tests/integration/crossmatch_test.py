import unittest

import structlog

from app.data import model, repositories
from app.domain import processing
from tests import lib


class CrossmatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()
        cls.layer2_repo = repositories.Layer2Repository(cls.pg_storage.get_storage(), structlog.get_logger())

    def tearDown(self):
        self.pg_storage.clear()

    def test_new_object(self):
        actual = processing.crossmatch(
            self.layer2_repo,
            [
                model.Layer0Object(
                    "1212",
                    [
                        model.ICRSCatalogObject(12, 0.1, 34, 0.1),
                        model.DesignationCatalogObject("M33"),
                    ],
                )
            ],
        )
        expected = {"1212": model.CIResultObjectNew()}

        self.assertEqual(actual, expected)

    def test_icrs_hit_designation_ambiguity(self):
        layer2_objects = [
            model.Layer2CatalogObject(123, model.ICRSCatalogObject(12, 0.1, 34.001, 0.1)),
            model.Layer2CatalogObject(123, model.DesignationCatalogObject("M33")),
            model.Layer2CatalogObject(456, model.DesignationCatalogObject("M34")),
        ]

        self.layer2_repo.save_data(layer2_objects)

        actual = processing.crossmatch(
            self.layer2_repo,
            [
                model.Layer0Object(
                    "1212",
                    [
                        model.ICRSCatalogObject(12, 0.1, 34, 0.1),
                        model.DesignationCatalogObject("M33"),
                    ],
                )
            ],
        )
        expected = {"1212": model.CIResultObjectExisting(123)}

        self.assertEqual(actual, expected)

    def test_both_ambiguous(self):
        layer2_objects = [
            model.Layer2CatalogObject(123, model.ICRSCatalogObject(12, 0.1, 34.001, 0.1)),
            model.Layer2CatalogObject(123, model.DesignationCatalogObject("M33")),
            model.Layer2CatalogObject(456, model.ICRSCatalogObject(12.001, 0.1, 34.001, 0.1)),
            model.Layer2CatalogObject(456, model.DesignationCatalogObject("M34")),
        ]

        self.layer2_repo.save_data(layer2_objects)

        actual = processing.crossmatch(
            self.layer2_repo,
            [
                model.Layer0Object(
                    "1212",
                    [
                        model.ICRSCatalogObject(12, 0.1, 34, 0.1),
                        model.DesignationCatalogObject("M33"),
                    ],
                )
            ],
        )
        expected = {
            "1212": model.CIResultObjectCollision({"icrs": {123, 456}, "designation": {123, 456}}),
        }

        self.assertEqual(actual, expected)

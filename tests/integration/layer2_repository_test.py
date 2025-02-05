import unittest

import structlog

from app.data import model, repositories
from app.data.repositories import layer2_repository
from tests import lib


class Layer2RepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()

        cls.layer2_repo = repositories.Layer2Repository(cls.pg_storage.get_storage(), structlog.get_logger())

    def tearDown(self):
        self.pg_storage.clear()

    def test_one_object(self):
        objects: list[model.Layer2CatalogObject] = [
            model.Layer2CatalogObject(1, model.DesignationCatalogObject(design="test")),
            model.Layer2CatalogObject(2, model.DesignationCatalogObject(design="test2")),
        ]

        self.layer2_repo.save_data(objects)

        actual = self.layer2_repo.query(
            [model.RawCatalog.DESIGNATION], [layer2_repository.DesignationEqualsFilter("test")], 10, 0
        )
        expected = model.Layer2CatalogObject(1, model.DesignationCatalogObject(design="test"))

        self.assertEqual(actual, [expected])

    def test_several_objects(self):
        objects: list[model.Layer2CatalogObject] = [
            model.Layer2CatalogObject(1, model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)),
            model.Layer2CatalogObject(2, model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)),
        ]

        self.layer2_repo.save_data(objects)

        actual = self.layer2_repo.query(
            [model.RawCatalog.ICRS], [layer2_repository.ICRSCoordinatesInRadiusFilter(12, 12, 10)], 10, 0
        )
        expected = objects

        self.assertEqual(actual, expected)

    def test_several_catalogs(self):
        objects = [
            model.Layer2CatalogObject(1, model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)),
            model.Layer2CatalogObject(2, model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)),
            model.Layer2CatalogObject(2, model.DesignationCatalogObject(design="test2")),
        ]

        self.layer2_repo.save_data(objects)

        actual = self.layer2_repo.query(
            [model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION],
            [layer2_repository.DesignationEqualsFilter("test2")],
            10,
            0,
        )
        expected = [
            model.Layer2CatalogObject(2, model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)),
            model.Layer2CatalogObject(2, model.DesignationCatalogObject(design="test2")),
        ]

        self.assertEqual(actual, expected)

    def test_several_filters(self):
        objects = [
            model.Layer2CatalogObject(1, model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)),
            model.Layer2CatalogObject(2, model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)),
            model.Layer2CatalogObject(2, model.DesignationCatalogObject(design="test2")),
            model.Layer2CatalogObject(1, model.DesignationCatalogObject(design="test")),
        ]

        self.layer2_repo.save_data(objects)

        actual = self.layer2_repo.query(
            [model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION],
            [
                layer2_repository.DesignationEqualsFilter("test2"),
                layer2_repository.ICRSCoordinatesInRadiusFilter(12, 12, 10),
            ],
            10,
            0,
        )
        expected = [
            model.Layer2CatalogObject(2, model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)),
            model.Layer2CatalogObject(2, model.DesignationCatalogObject(design="test2")),
        ]

        self.assertEqual(actual, expected)

    def test_pagination(self):
        objects: list[model.Layer2CatalogObject] = [
            model.Layer2CatalogObject(1, model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)),
            model.Layer2CatalogObject(2, model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)),
            model.Layer2CatalogObject(3, model.ICRSCatalogObject(ra=12, dec=12, e_ra=0.1, e_dec=0.1)),
            model.Layer2CatalogObject(4, model.ICRSCatalogObject(ra=13, dec=13, e_ra=0.1, e_dec=0.1)),
            model.Layer2CatalogObject(5, model.ICRSCatalogObject(ra=14, dec=14, e_ra=0.1, e_dec=0.1)),
        ]

        self.layer2_repo.save_data(objects)

        actual = self.layer2_repo.query(
            [model.RawCatalog.ICRS],
            [layer2_repository.ICRSCoordinatesInRadiusFilter(12, 12, 10)],
            2,
            1,
        )

        self.assertEqual(len(actual), 2)

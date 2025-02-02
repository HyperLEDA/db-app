import unittest

import structlog

from app.data import model, repositories
from app.data.repositories import layer2_repository
from tests import lib


class Layer2RepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.get_test_postgres_storage()

        cls.layer2_repo = repositories.Layer2Repository(cls.pg_storage.get_storage(), structlog.get_logger())

    def tearDown(self):
        self.pg_storage.clear()

    def test_one_object(self):
        objects: list[model.CatalogObject] = [
            model.DesignationCatalogObject(pgc=1, design="test"),
            model.DesignationCatalogObject(pgc=2, design="test2"),
        ]

        self.layer2_repo.save_data(objects)

        actual = self.layer2_repo.query(
            [model.RawCatalog.DESIGNATION], [layer2_repository.DesignationEqualsFilter("test")], 10, 0
        )
        expected = model.DesignationCatalogObject(pgc=1, design="test")

        self.assertEqual(actual, [expected])

    def test_several_objects(self):
        objects: list[model.CatalogObject] = [
            model.ICRSCatalogObject(pgc=1, ra=10, dec=10, e_ra=0.1, e_dec=0.1),
            model.ICRSCatalogObject(pgc=2, ra=11, dec=11, e_ra=0.1, e_dec=0.1),
        ]

        self.layer2_repo.save_data(objects)

        actual = self.layer2_repo.query(
            [model.RawCatalog.ICRS], [layer2_repository.ICRSCoordinatesInRadiusFilter(12, 12, 10)], 10, 0
        )
        expected = objects

        self.assertEqual(actual, expected)

    def test_several_catalogs(self):
        objects = [
            model.ICRSCatalogObject(pgc=1, ra=10, dec=10, e_ra=0.1, e_dec=0.1),
            model.ICRSCatalogObject(pgc=2, ra=11, dec=11, e_ra=0.1, e_dec=0.1),
            model.DesignationCatalogObject(pgc=2, design="test2"),
        ]

        self.layer2_repo.save_data(objects)

        actual = self.layer2_repo.query(
            [model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION],
            [layer2_repository.DesignationEqualsFilter("test2")],
            10,
            0,
        )
        expected = [
            model.ICRSCatalogObject(pgc=2, ra=11, dec=11, e_ra=0.1, e_dec=0.1),
            model.DesignationCatalogObject(pgc=2, design="test2"),
        ]

        self.assertEqual(actual, expected)

    def test_several_filters(self):
        objects = [
            model.ICRSCatalogObject(pgc=1, ra=10, dec=10, e_ra=0.1, e_dec=0.1),
            model.ICRSCatalogObject(pgc=2, ra=11, dec=11, e_ra=0.1, e_dec=0.1),
            model.DesignationCatalogObject(pgc=2, design="test2"),
            model.DesignationCatalogObject(pgc=1, design="test"),
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
            model.ICRSCatalogObject(pgc=2, ra=11, dec=11, e_ra=0.1, e_dec=0.1),
            model.DesignationCatalogObject(pgc=2, design="test2"),
        ]

        self.assertEqual(actual, expected)

    def test_pagination(self):
        objects: list[model.CatalogObject] = [
            model.ICRSCatalogObject(pgc=1, ra=10, dec=10, e_ra=0.1, e_dec=0.1),
            model.ICRSCatalogObject(pgc=2, ra=11, dec=11, e_ra=0.1, e_dec=0.1),
            model.ICRSCatalogObject(pgc=3, ra=12, dec=12, e_ra=0.1, e_dec=0.1),
            model.ICRSCatalogObject(pgc=4, ra=13, dec=13, e_ra=0.1, e_dec=0.1),
            model.ICRSCatalogObject(pgc=5, ra=14, dec=14, e_ra=0.1, e_dec=0.1),
        ]

        self.layer2_repo.save_data(objects)

        actual = self.layer2_repo.query(
            [model.RawCatalog.ICRS],
            [layer2_repository.ICRSCoordinatesInRadiusFilter(12, 12, 10)],
            2,
            1,
        )

        self.assertEqual(len(actual), 2)

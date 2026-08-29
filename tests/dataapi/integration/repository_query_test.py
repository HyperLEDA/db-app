import unittest

import structlog
from astropy import units as u

from app import catalogs
from app.dataapi import repository
from app.lib.storage import enums
from tests import lib
from tests.lib import layer_seed


class RepositoryQueryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get(enums.PG_ENUM_REGISTRY)

        cls.repo = repository.Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.storage = cls.pg_storage.get_storage()

    def tearDown(self):
        self.pg_storage.clear()

    def _save_layer2_data(self, objects: list[catalogs.Layer2CatalogObject]) -> None:
        storage = self.pg_storage.get_storage()
        by_table: dict[str, list[tuple[int, catalogs.CatalogObject]]] = {}
        for obj in objects:
            for catalog_obj in obj.data:
                layer2_table = catalog_obj.layer2_table()
                if layer2_table not in by_table:
                    by_table[layer2_table] = []
                by_table[layer2_table].append((obj.pgc, catalog_obj))
        for table_name, table_entries in by_table.items():
            if not table_entries:
                continue
            columns = table_entries[0][1].layer2_keys()
            all_columns = ["pgc", *columns]
            placeholders = ", ".join(["%s"] * len(all_columns))
            update_set = ", ".join(f"{col} = EXCLUDED.{col}" for col in all_columns)
            query = (
                f"INSERT INTO {table_name} ({', '.join(all_columns)}) "
                f"VALUES ({placeholders}) ON CONFLICT (pgc) DO UPDATE SET {update_set}"
            )
            rows = [[pgc, *[catalog_obj.layer2_data()[col] for col in columns]] for pgc, catalog_obj in table_entries]
            storage.execute_batch(query, rows)

    def _get_table(self, table_name: str) -> int:
        bib_id = layer_seed.create_bibliography(self.storage, "123456", 2000, ["test"], "test")
        return layer_seed.create_table(self.storage, table_name, bib_id)

    def test_one_object(self):
        objects: list[catalogs.Layer2CatalogObject] = [
            catalogs.Layer2CatalogObject(1, [catalogs.DesignationCatalogObject(design="test")]),
            catalogs.Layer2CatalogObject(2, [catalogs.DesignationCatalogObject(design="test2")]),
        ]

        layer_seed.register_pgcs(self.storage, [1, 2])
        self._save_layer2_data(objects)

        actual = self.repo.query_catalogs(
            [catalogs.RawCatalog.DESIGNATION],
            repository.PGCOneOfFilter([1]),
            repository.CombinedSearchParams([]),
            10,
            0,
        )
        expected = [catalogs.Layer2CatalogObject(1, [catalogs.DesignationCatalogObject(design="test")])]

        lib.assert_layer2_catalog_objects_equal(self, actual, expected)

    def test_several_objects(self):
        objects: list[catalogs.Layer2CatalogObject] = [
            catalogs.Layer2CatalogObject(1, [catalogs.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(2, [catalogs.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)]),
        ]

        layer_seed.register_pgcs(self.storage, [1, 2])
        self._save_layer2_data(objects)

        actual = self.repo.query_catalogs(
            [catalogs.RawCatalog.ICRS],
            repository.ICRSCoordinatesInRadiusFilter(10 * u.Unit("deg")),
            repository.ICRSSearchParams(12 * u.Unit("deg"), 12 * u.Unit("deg")),
            10,
            0,
            ordering=repository.ICRSDistanceOrdering(12 * u.Unit("deg"), 12 * u.Unit("deg")),
        )
        expected = [
            catalogs.Layer2CatalogObject(2, [catalogs.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(1, [catalogs.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
        ]

        lib.assert_layer2_catalog_objects_equal(self, actual, expected)

    def test_several_catalogs(self):
        objects = [
            catalogs.Layer2CatalogObject(1, [catalogs.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(
                2,
                [
                    catalogs.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1),
                    catalogs.DesignationCatalogObject(design="test2"),
                ],
            ),
        ]

        layer_seed.register_pgcs(self.storage, [1, 2])
        self._save_layer2_data(objects)

        actual = self.repo.query_catalogs(
            [catalogs.RawCatalog.ICRS, catalogs.RawCatalog.DESIGNATION],
            repository.PGCOneOfFilter([2]),
            repository.CombinedSearchParams([]),
            10,
            0,
        )
        expected = [
            catalogs.Layer2CatalogObject(
                2,
                [
                    catalogs.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1),
                    catalogs.DesignationCatalogObject(design="test2"),
                ],
            ),
        ]

        lib.assert_layer2_catalog_objects_equal(self, actual, expected)

    def test_several_filters(self):
        objects = [
            catalogs.Layer2CatalogObject(
                1,
                [
                    catalogs.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1),
                    catalogs.DesignationCatalogObject(design="test"),
                ],
            ),
            catalogs.Layer2CatalogObject(
                2,
                [
                    catalogs.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1),
                    catalogs.DesignationCatalogObject(design="test2"),
                ],
            ),
        ]

        layer_seed.register_pgcs(self.storage, [1, 2])
        self._save_layer2_data(objects)

        actual = self.repo.query_catalogs(
            [catalogs.RawCatalog.ICRS, catalogs.RawCatalog.DESIGNATION],
            repository.AndFilter(
                [
                    repository.PGCOneOfFilter([2]),
                    repository.ICRSCoordinatesInRadiusFilter(10 * u.Unit("deg")),
                ]
            ),
            repository.CombinedSearchParams(
                [
                    repository.ICRSSearchParams(12 * u.Unit("deg"), 12 * u.Unit("deg")),
                ]
            ),
            10,
            0,
        )

        expected = [
            catalogs.Layer2CatalogObject(
                2,
                [
                    catalogs.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1),
                    catalogs.DesignationCatalogObject(design="test2"),
                ],
            )
        ]

        lib.assert_layer2_catalog_objects_equal(self, actual, expected)

    def test_pagination(self):
        objects: list[catalogs.Layer2CatalogObject] = [
            catalogs.Layer2CatalogObject(1, [catalogs.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(2, [catalogs.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(3, [catalogs.ICRSCatalogObject(ra=12, dec=12, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(4, [catalogs.ICRSCatalogObject(ra=13, dec=13, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(5, [catalogs.ICRSCatalogObject(ra=14, dec=14, e_ra=0.1, e_dec=0.1)]),
        ]

        layer_seed.register_pgcs(self.storage, [1, 2, 3, 4, 5])
        self._save_layer2_data(objects)

        actual = self.repo.query_catalogs(
            [catalogs.RawCatalog.ICRS],
            repository.ICRSCoordinatesInRadiusFilter(10 * u.Unit("deg")),
            repository.ICRSSearchParams(12 * u.Unit("deg"), 12 * u.Unit("deg")),
            2,
            1,
        )

        self.assertEqual(len(actual), 2)

    def test_batch_query(self):
        objects: list[catalogs.Layer2CatalogObject] = [
            catalogs.Layer2CatalogObject(1, [catalogs.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(2, [catalogs.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(3, [catalogs.ICRSCatalogObject(ra=12, dec=12, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(4, [catalogs.ICRSCatalogObject(ra=13, dec=13, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(5, [catalogs.ICRSCatalogObject(ra=14, dec=14, e_ra=0.1, e_dec=0.1)]),
        ]

        layer_seed.register_pgcs(self.storage, [1, 2, 3, 4, 5])
        self._save_layer2_data(objects)

        actual = self.repo.query_catalogs_batch(
            [catalogs.RawCatalog.ICRS],
            {"icrs": repository.ICRSCoordinatesInRadiusFilter(10 * u.Unit("deg"))},
            {
                "obj1": repository.ICRSSearchParams(10 * u.Unit("deg"), 10 * u.Unit("deg")),
                "obj2": repository.ICRSSearchParams(13 * u.Unit("deg"), 13 * u.Unit("deg")),
            },
            20,
            0,
        )

        self.assertEqual(len(actual), 2)

    def _query_icrs_in_radius(
        self,
        ra: float,
        dec: float,
        radius: float,
        raw_catalogs: list[catalogs.RawCatalog] | None = None,
        ordering: repository.Ordering | None = None,
    ) -> list[catalogs.Layer2CatalogObject]:
        return self.repo.query_catalogs(
            raw_catalogs or [catalogs.RawCatalog.ICRS],
            repository.ICRSCoordinatesInRadiusFilter(radius * u.Unit("deg")),
            repository.ICRSSearchParams(ra * u.Unit("deg"), dec * u.Unit("deg")),
            10,
            0,
            ordering=ordering,
        )

    def test_cone_search_wraps_around_ra_zero(self):
        objects: list[catalogs.Layer2CatalogObject] = [
            catalogs.Layer2CatalogObject(1, [catalogs.ICRSCatalogObject(ra=359.99, dec=0, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(2, [catalogs.ICRSCatalogObject(ra=0.01, dec=0, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(3, [catalogs.ICRSCatalogObject(ra=180, dec=0, e_ra=0.1, e_dec=0.1)]),
        ]

        layer_seed.register_pgcs(self.storage, [1, 2, 3])
        self._save_layer2_data(objects)

        actual = self._query_icrs_in_radius(ra=0.0, dec=0.0, radius=0.05)

        self.assertEqual({obj.pgc for obj in actual}, {1, 2})

    def test_cone_search_accounts_for_declination_convergence(self):
        objects: list[catalogs.Layer2CatalogObject] = [
            catalogs.Layer2CatalogObject(1, [catalogs.ICRSCatalogObject(ra=100, dec=80, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(2, [catalogs.ICRSCatalogObject(ra=102, dec=80, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(3, [catalogs.ICRSCatalogObject(ra=100, dec=79, e_ra=0.1, e_dec=0.1)]),
        ]

        layer_seed.register_pgcs(self.storage, [1, 2, 3])
        self._save_layer2_data(objects)

        actual = self._query_icrs_in_radius(ra=100.0, dec=80.0, radius=0.5)

        self.assertEqual({obj.pgc for obj in actual}, {1, 2})

    def test_distance_ordering_sorts_by_true_angular_separation(self):
        objects: list[catalogs.Layer2CatalogObject] = [
            catalogs.Layer2CatalogObject(1, [catalogs.ICRSCatalogObject(ra=14, dec=60, e_ra=0.1, e_dec=0.1)]),
            catalogs.Layer2CatalogObject(2, [catalogs.ICRSCatalogObject(ra=10, dec=62.5, e_ra=0.1, e_dec=0.1)]),
        ]

        layer_seed.register_pgcs(self.storage, [1, 2])
        self._save_layer2_data(objects)

        actual = self._query_icrs_in_radius(
            ra=10.0,
            dec=60.0,
            radius=5.0,
            ordering=repository.ICRSDistanceOrdering(10 * u.Unit("deg"), 60 * u.Unit("deg")),
        )

        self.assertEqual([obj.pgc for obj in actual], [1, 2])

    def test_coordinate_filter_when_icrs_catalog_not_requested(self):
        objects = [
            catalogs.Layer2CatalogObject(
                1,
                [
                    catalogs.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1),
                    catalogs.RedshiftCatalogObject(cz=100, e_cz=1),
                ],
            ),
        ]

        layer_seed.register_pgcs(self.storage, [1])
        self._save_layer2_data(objects)

        actual = self._query_icrs_in_radius(
            ra=10.0,
            dec=10.0,
            radius=1.0,
            raw_catalogs=[catalogs.RawCatalog.REDSHIFT],
        )

        lib.assert_layer2_catalog_objects_equal(
            self,
            actual,
            [catalogs.Layer2CatalogObject(1, [catalogs.RedshiftCatalogObject(cz=100, e_cz=1)])],
        )

    def test_designation_filter_when_designation_catalog_not_requested(self):
        objects = [
            catalogs.Layer2CatalogObject(
                1,
                [
                    catalogs.DesignationCatalogObject(design="test"),
                    catalogs.RedshiftCatalogObject(cz=100, e_cz=1),
                ],
            ),
        ]

        layer_seed.register_pgcs(self.storage, [1])
        self._save_layer2_data(objects)

        actual = self.repo.query_catalogs(
            [catalogs.RawCatalog.REDSHIFT],
            repository.PGCOneOfFilter([1]),
            repository.CombinedSearchParams([]),
            10,
            0,
        )

        lib.assert_layer2_catalog_objects_equal(
            self,
            actual,
            [catalogs.Layer2CatalogObject(1, [catalogs.RedshiftCatalogObject(cz=100, e_cz=1)])],
        )

    def test_query_photometry_total(self) -> None:
        self._get_table("phot_table")
        layer_seed.register_records(self.storage, "phot_table", ["r1"])
        layer_seed.register_pgcs(self.storage, [5001])
        layer_seed.upsert_pgc(self.storage, {"r1": 5001})
        layer_seed.save_structured_data(
            self.storage,
            catalogs.PhotometryTotalCatalogObject.layer1_table(),
            ["band", "mag", "e_mag", "method"],
            ["r1"],
            [["V", 12.5, 0.1, "psf"]],
            conflict_keys=catalogs.PhotometryTotalCatalogObject.layer1_primary_keys(),
        )

        result = self.repo.query_pgc([catalogs.RawCatalog.PHOTOMETRY__TOTAL], [5001], limit=10)

        self.assertEqual(len(result), 1)
        photometry = result[0].catalogs.photometry_total
        self.assertIsNotNone(photometry)
        assert photometry is not None
        self.assertEqual(len(photometry.measurements), 1)
        measurement = photometry.measurements[0]
        self.assertEqual(measurement.band, "V")
        self.assertEqual(measurement.magsys, "Vega")
        self.assertEqual(measurement.method, "psf")
        self.assertEqual(measurement.photsys, "UBVRIJHKL")
        self.assertEqual(measurement.filter, "V")
        self.assertAlmostEqual(measurement.wavelength, 5501.40)
        self.assertAlmostEqual(measurement.mag, 12.5)
        self.assertIsNotNone(measurement.e_mag)
        assert measurement.e_mag is not None
        self.assertAlmostEqual(measurement.e_mag, 0.1)

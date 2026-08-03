import datetime
import unittest

import structlog
from astropy import table
from astropy import units as u

from app.data import model, repositories
from app.data.repositories import layer2
from tests import lib


class Layer2RepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()

        cls.common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer1_repo = repositories.Layer1Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer2_repo = repositories.Layer2Repository(cls.pg_storage.get_storage(), structlog.get_logger())

    def tearDown(self):
        self.pg_storage.clear()

    def _save_layer2_data(self, objects: list[model.Layer2CatalogObject]) -> None:
        by_table: dict[str, list[tuple[int, model.CatalogObject]]] = {}
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
            qtable_data: dict[str, list[object]] = {"pgc": [pgc for pgc, _ in table_entries]}
            for column in columns:
                qtable_data[column] = [catalog_obj.layer2_data()[column] for _, catalog_obj in table_entries]
            self.layer2_repo.save(table_name, table.QTable(qtable_data))

    def _get_table(self, table_name: str) -> int:
        bib_id = self.common_repo.create_bibliography("123456", 2000, ["test"], "test")
        table_resp = self.layer0_repo.create_table(model.Layer0TableMeta(table_name, [], bib_id))
        return table_resp.table_id

    def test_one_object(self):
        objects: list[model.Layer2CatalogObject] = [
            model.Layer2CatalogObject(1, [model.DesignationCatalogObject(design="test")]),
            model.Layer2CatalogObject(2, [model.DesignationCatalogObject(design="test2")]),
        ]

        self.common_repo.register_pgcs([1, 2])
        self._save_layer2_data(objects)

        actual = self.layer2_repo.query_catalogs(
            [model.RawCatalog.DESIGNATION],
            layer2.DesignationEqualsFilter("test"),
            layer2.CombinedSearchParams([]),
            10,
            0,
        )
        expected = [model.Layer2CatalogObject(1, [model.DesignationCatalogObject(design="test")])]

        lib.assert_layer2_catalog_objects_equal(self, actual, expected)

    def test_several_objects(self):
        objects: list[model.Layer2CatalogObject] = [
            model.Layer2CatalogObject(1, [model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(2, [model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)]),
        ]

        self.common_repo.register_pgcs([1, 2])
        self._save_layer2_data(objects)

        actual = self.layer2_repo.query_catalogs(
            [model.RawCatalog.ICRS],
            layer2.ICRSCoordinatesInRadiusFilter(10 * u.Unit("deg")),
            layer2.ICRSSearchParams(12 * u.Unit("deg"), 12 * u.Unit("deg")),
            10,
            0,
            ordering=layer2.ICRSDistanceOrdering(12 * u.Unit("deg"), 12 * u.Unit("deg")),
        )
        expected = [
            model.Layer2CatalogObject(2, [model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(1, [model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
        ]

        lib.assert_layer2_catalog_objects_equal(self, actual, expected)

    def test_several_catalogs(self):
        objects = [
            model.Layer2CatalogObject(1, [model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(
                2,
                [
                    model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1),
                    model.DesignationCatalogObject(design="test2"),
                ],
            ),
        ]

        self.common_repo.register_pgcs([1, 2])
        self._save_layer2_data(objects)

        actual = self.layer2_repo.query_catalogs(
            [model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION],
            layer2.DesignationEqualsFilter("test2"),
            layer2.CombinedSearchParams([]),
            10,
            0,
        )
        expected = [
            model.Layer2CatalogObject(
                2,
                [
                    model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1),
                    model.DesignationCatalogObject(design="test2"),
                ],
            ),
        ]

        lib.assert_layer2_catalog_objects_equal(self, actual, expected)

    def test_several_filters(self):
        objects = [
            model.Layer2CatalogObject(
                1,
                [
                    model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1),
                    model.DesignationCatalogObject(design="test"),
                ],
            ),
            model.Layer2CatalogObject(
                2,
                [
                    model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1),
                    model.DesignationCatalogObject(design="test2"),
                ],
            ),
        ]

        self.common_repo.register_pgcs([1, 2])
        self._save_layer2_data(objects)

        actual = self.layer2_repo.query_catalogs(
            [model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION],
            layer2.AndFilter(
                [
                    layer2.DesignationEqualsFilter("test2"),
                    layer2.ICRSCoordinatesInRadiusFilter(10 * u.Unit("deg")),
                ]
            ),
            layer2.CombinedSearchParams(
                [
                    layer2.ICRSSearchParams(12 * u.Unit("deg"), 12 * u.Unit("deg")),
                ]
            ),
            10,
            0,
        )

        expected = [
            model.Layer2CatalogObject(
                2,
                [
                    model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1),
                    model.DesignationCatalogObject(design="test2"),
                ],
            )
        ]

        lib.assert_layer2_catalog_objects_equal(self, actual, expected)

    def test_pagination(self):
        objects: list[model.Layer2CatalogObject] = [
            model.Layer2CatalogObject(1, [model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(2, [model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(3, [model.ICRSCatalogObject(ra=12, dec=12, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(4, [model.ICRSCatalogObject(ra=13, dec=13, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(5, [model.ICRSCatalogObject(ra=14, dec=14, e_ra=0.1, e_dec=0.1)]),
        ]

        self.common_repo.register_pgcs([1, 2, 3, 4, 5])
        self._save_layer2_data(objects)

        actual = self.layer2_repo.query_catalogs(
            [model.RawCatalog.ICRS],
            layer2.ICRSCoordinatesInRadiusFilter(10 * u.Unit("deg")),
            layer2.ICRSSearchParams(12 * u.Unit("deg"), 12 * u.Unit("deg")),
            2,
            1,
        )

        self.assertEqual(len(actual), 2)

    def test_batch_query(self):
        objects: list[model.Layer2CatalogObject] = [
            model.Layer2CatalogObject(1, [model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(2, [model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(3, [model.ICRSCatalogObject(ra=12, dec=12, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(4, [model.ICRSCatalogObject(ra=13, dec=13, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(5, [model.ICRSCatalogObject(ra=14, dec=14, e_ra=0.1, e_dec=0.1)]),
        ]

        self.common_repo.register_pgcs([1, 2, 3, 4, 5])
        self._save_layer2_data(objects)

        actual = self.layer2_repo.query_catalogs_batch(
            [model.RawCatalog.ICRS],
            {"icrs": layer2.ICRSCoordinatesInRadiusFilter(10 * u.Unit("deg"))},
            {
                "obj1": layer2.ICRSSearchParams(10 * u.Unit("deg"), 10 * u.Unit("deg")),
                "obj2": layer2.ICRSSearchParams(13 * u.Unit("deg"), 13 * u.Unit("deg")),
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
        catalogs: list[model.RawCatalog] | None = None,
        ordering: layer2.Ordering | None = None,
    ) -> list[model.Layer2CatalogObject]:
        return self.layer2_repo.query_catalogs(
            catalogs or [model.RawCatalog.ICRS],
            layer2.ICRSCoordinatesInRadiusFilter(radius * u.Unit("deg")),
            layer2.ICRSSearchParams(ra * u.Unit("deg"), dec * u.Unit("deg")),
            10,
            0,
            ordering=ordering,
        )

    def test_cone_search_wraps_around_ra_zero(self):
        objects: list[model.Layer2CatalogObject] = [
            model.Layer2CatalogObject(1, [model.ICRSCatalogObject(ra=359.99, dec=0, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(2, [model.ICRSCatalogObject(ra=0.01, dec=0, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(3, [model.ICRSCatalogObject(ra=180, dec=0, e_ra=0.1, e_dec=0.1)]),
        ]

        self.common_repo.register_pgcs([1, 2, 3])
        self._save_layer2_data(objects)

        actual = self._query_icrs_in_radius(ra=0.0, dec=0.0, radius=0.05)

        self.assertEqual({obj.pgc for obj in actual}, {1, 2})

    def test_cone_search_accounts_for_declination_convergence(self):
        # At dec=+80 a 2 degree offset in RA is only ~0.3 degrees of true angular separation,
        # so pgc 2 is inside a 0.5 degree cone even though its RA differs by far more than that.
        objects: list[model.Layer2CatalogObject] = [
            model.Layer2CatalogObject(1, [model.ICRSCatalogObject(ra=100, dec=80, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(2, [model.ICRSCatalogObject(ra=102, dec=80, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(3, [model.ICRSCatalogObject(ra=100, dec=79, e_ra=0.1, e_dec=0.1)]),
        ]

        self.common_repo.register_pgcs([1, 2, 3])
        self._save_layer2_data(objects)

        actual = self._query_icrs_in_radius(ra=100.0, dec=80.0, radius=0.5)

        self.assertEqual({obj.pgc for obj in actual}, {1, 2})

    def test_distance_ordering_sorts_by_true_angular_separation(self):
        # pgc 1 is 2.0 degrees away and pgc 2 is 2.5 degrees away. Swapping ra and dec in the
        # ordering expression would reverse this, so the order pins down the argument order.
        objects: list[model.Layer2CatalogObject] = [
            model.Layer2CatalogObject(1, [model.ICRSCatalogObject(ra=14, dec=60, e_ra=0.1, e_dec=0.1)]),
            model.Layer2CatalogObject(2, [model.ICRSCatalogObject(ra=10, dec=62.5, e_ra=0.1, e_dec=0.1)]),
        ]

        self.common_repo.register_pgcs([1, 2])
        self._save_layer2_data(objects)

        actual = self._query_icrs_in_radius(
            ra=10.0,
            dec=60.0,
            radius=5.0,
            ordering=layer2.ICRSDistanceOrdering(10 * u.Unit("deg"), 60 * u.Unit("deg")),
        )

        self.assertEqual([obj.pgc for obj in actual], [1, 2])

    def test_coordinate_filter_when_icrs_catalog_not_requested(self):
        objects = [
            model.Layer2CatalogObject(
                1,
                [
                    model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1),
                    model.RedshiftCatalogObject(cz=100, e_cz=1),
                ],
            ),
        ]

        self.common_repo.register_pgcs([1])
        self._save_layer2_data(objects)

        actual = self._query_icrs_in_radius(
            ra=10.0,
            dec=10.0,
            radius=1.0,
            catalogs=[model.RawCatalog.REDSHIFT],
        )

        lib.assert_layer2_catalog_objects_equal(
            self,
            actual,
            [model.Layer2CatalogObject(1, [model.RedshiftCatalogObject(cz=100, e_cz=1)])],
        )

    def test_designation_filter_when_designation_catalog_not_requested(self):
        objects = [
            model.Layer2CatalogObject(
                1,
                [
                    model.DesignationCatalogObject(design="test"),
                    model.RedshiftCatalogObject(cz=100, e_cz=1),
                ],
            ),
        ]

        self.common_repo.register_pgcs([1])
        self._save_layer2_data(objects)

        actual = self.layer2_repo.query_catalogs(
            [model.RawCatalog.REDSHIFT],
            layer2.DesignationEqualsFilter("test"),
            layer2.CombinedSearchParams([]),
            10,
            0,
        )

        lib.assert_layer2_catalog_objects_equal(
            self,
            actual,
            [model.Layer2CatalogObject(1, [model.RedshiftCatalogObject(cz=100, e_cz=1)])],
        )

    def test_get_last_update_time_returns_stored_dt(self) -> None:
        dt_icrs = self.layer2_repo.get_last_update_time(model.RawCatalog.ICRS)
        dt_nature = self.layer2_repo.get_last_update_time(model.RawCatalog.NATURE)
        epoch = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)
        self.assertEqual(dt_icrs if dt_icrs.tzinfo else dt_icrs.replace(tzinfo=datetime.UTC), epoch)
        self.assertEqual(
            dt_nature if dt_nature.tzinfo else dt_nature.replace(tzinfo=datetime.UTC),
            epoch,
        )

    def test_update_last_update_time_updates_stored_dt(self) -> None:
        new_dt = datetime.datetime(2020, 6, 15, 12, 0, 0, tzinfo=datetime.UTC)
        self.layer2_repo.update_last_update_time(new_dt, model.RawCatalog.ICRS)

        got_icrs = self.layer2_repo.get_last_update_time(model.RawCatalog.ICRS)
        self.assertEqual(got_icrs.replace(tzinfo=None), new_dt.replace(tzinfo=None))
        got_nature = self.layer2_repo.get_last_update_time(model.RawCatalog.NATURE)
        epoch = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)
        self.assertEqual(
            got_nature if got_nature.tzinfo else got_nature.replace(tzinfo=datetime.UTC),
            epoch,
        )

    def test_get_orphaned_pgcs_returns_pgcs_without_layer1_data(self) -> None:
        self.common_repo.register_pgcs([1, 2])
        self._save_layer2_data(
            [
                model.Layer2CatalogObject(1, [model.DesignationCatalogObject(design="a")]),
                model.Layer2CatalogObject(2, [model.DesignationCatalogObject(design="b")]),
            ]
        )

        orphaned = self.layer2_repo.get_orphaned_pgcs([model.RawCatalog.DESIGNATION])

        self.assertEqual(orphaned.keys(), {"layer2.designation"})
        self.assertEqual(set(orphaned["layer2.designation"]), {1, 2})

    def test_get_orphaned_pgcs_returns_empty_when_layer1_present(self) -> None:
        self._get_table("t1")
        self.layer0_repo.register_records("t1", ["r1"])
        self.common_repo.register_pgcs([100])
        self.layer0_repo.upsert_pgc({"r1": 100})
        self.layer1_repo.save_structured_data(
            "designation.data",
            ["design"],
            ["r1"],
            [["x"]],
            conflict_keys=model.DesignationCatalogObject.layer1_primary_keys(),
        )
        self._save_layer2_data([model.Layer2CatalogObject(100, [model.DesignationCatalogObject(design="x")])])

        orphaned = self.layer2_repo.get_orphaned_pgcs([model.RawCatalog.DESIGNATION])

        self.assertEqual(orphaned, {"layer2.designation": []})

    def test_get_orphaned_pgcs_returns_only_pgcs_without_layer1_data(self) -> None:
        self._get_table("t1")
        self.layer0_repo.register_records("t1", ["r1"])
        self.common_repo.register_pgcs([100, 200])
        self.layer0_repo.upsert_pgc({"r1": 100})
        self.layer1_repo.save_structured_data(
            "designation.data",
            ["design"],
            ["r1"],
            [["linked"]],
            conflict_keys=model.DesignationCatalogObject.layer1_primary_keys(),
        )
        self._save_layer2_data(
            [
                model.Layer2CatalogObject(100, [model.DesignationCatalogObject(design="linked")]),
                model.Layer2CatalogObject(200, [model.DesignationCatalogObject(design="orphan")]),
            ]
        )

        orphaned = self.layer2_repo.get_orphaned_pgcs([model.RawCatalog.DESIGNATION])

        self.assertEqual(orphaned.keys(), {"layer2.designation"})
        self.assertEqual(set(orphaned["layer2.designation"]), {200})

    def test_remove_pgcs_removes_specified_pgcs(self) -> None:
        self.common_repo.register_pgcs([1, 2])
        self._save_layer2_data(
            [
                model.Layer2CatalogObject(1, [model.DesignationCatalogObject(design="d1")]),
                model.Layer2CatalogObject(2, [model.DesignationCatalogObject(design="d2")]),
            ]
        )

        self.layer2_repo.remove_pgcs([model.RawCatalog.DESIGNATION], [1])

        actual = self.layer2_repo.query_catalogs(
            [model.RawCatalog.DESIGNATION],
            layer2.DesignationEqualsFilter("d1"),
            layer2.CombinedSearchParams([]),
            10,
            0,
        )
        self.assertEqual(actual, [])
        actual = self.layer2_repo.query_catalogs(
            [model.RawCatalog.DESIGNATION],
            layer2.DesignationEqualsFilter("d2"),
            layer2.CombinedSearchParams([]),
            10,
            0,
        )
        lib.assert_layer2_catalog_objects_equal(
            self,
            actual,
            [model.Layer2CatalogObject(2, [model.DesignationCatalogObject(design="d2")])],
        )

    def test_query_photometry_total(self) -> None:
        self._get_table("phot_table")
        self.layer0_repo.register_records("phot_table", ["r1"])
        self.common_repo.register_pgcs([5001])
        self.layer0_repo.upsert_pgc({"r1": 5001})
        self.layer1_repo.save_structured_data(
            model.PhotometryTotalCatalogObject.layer1_table(),
            ["band", "mag", "e_mag", "method"],
            ["r1"],
            [["V", 12.5, 0.1, "psf"]],
            conflict_keys=model.PhotometryTotalCatalogObject.layer1_primary_keys(),
        )

        result = self.layer2_repo.query_pgc([model.RawCatalog.PHOTOMETRY__TOTAL], [5001], limit=10)

        self.assertEqual(len(result), 1)
        photometry = result[0].catalogs.photometry_total
        self.assertIsNotNone(photometry)
        assert photometry is not None
        self.assertEqual(len(photometry.measurements), 1)
        measurement = photometry.measurements[0]
        self.assertEqual(measurement.band, "V")
        self.assertEqual(measurement.magsys, "Vega")
        self.assertEqual(measurement.method, "psf")
        self.assertAlmostEqual(measurement.wavelength, 5501.40)
        self.assertAlmostEqual(measurement.mag, 12.5)
        self.assertIsNotNone(measurement.e_mag)
        assert measurement.e_mag is not None
        self.assertAlmostEqual(measurement.e_mag, 0.1)

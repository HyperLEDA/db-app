import datetime
import unittest

import structlog

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

    def _save_layer2_data(self, objects: list[model.Layer2Object]) -> None:
        by_table: dict[str, list[tuple[int, model.CatalogObject]]] = {}
        for obj in objects:
            for catalog_obj in obj.data:
                table = catalog_obj.layer2_table()
                if table not in by_table:
                    by_table[table] = []
                by_table[table].append((obj.pgc, catalog_obj))
        for table, table_entries in by_table.items():
            if not table_entries:
                continue
            columns = table_entries[0][1].layer2_keys()
            pgcs = [pgc for pgc, _ in table_entries]
            data = [[catalog_obj.layer2_data()[c] for c in columns] for _, catalog_obj in table_entries]
            self.layer2_repo.save(table, columns, pgcs, data)

    def _get_table(self, table_name: str) -> int:
        bib_id = self.common_repo.create_bibliography("123456", 2000, ["test"], "test")
        table_resp = self.layer0_repo.create_table(model.Layer0TableMeta(table_name, [], bib_id))
        return table_resp.table_id

    def test_one_object(self):
        objects: list[model.Layer2Object] = [
            model.Layer2Object(1, [model.DesignationCatalogObject(design="test")]),
            model.Layer2Object(2, [model.DesignationCatalogObject(design="test2")]),
        ]

        self.common_repo.register_pgcs([1, 2])
        self._save_layer2_data(objects)

        actual = self.layer2_repo.query(
            [model.RawCatalog.DESIGNATION],
            layer2.DesignationEqualsFilter("test"),
            layer2.CombinedSearchParams([]),
            10,
            0,
        )
        expected = [model.Layer2Object(1, [model.DesignationCatalogObject(design="test")])]

        self.assertEqual(actual, expected)

    def test_several_objects(self):
        objects: list[model.Layer2Object] = [
            model.Layer2Object(1, [model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
            model.Layer2Object(2, [model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)]),
        ]

        self.common_repo.register_pgcs([1, 2])
        self._save_layer2_data(objects)

        actual = self.layer2_repo.query(
            [model.RawCatalog.ICRS],
            layer2.ICRSCoordinatesInRadiusFilter(10),
            layer2.ICRSSearchParams(12, 12),
            10,
            0,
        )
        expected = [
            model.Layer2Object(1, [model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
            model.Layer2Object(2, [model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)]),
        ]

        self.assertEqual(actual, expected)

    def test_several_catalogs(self):
        objects = [
            model.Layer2Object(1, [model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
            model.Layer2Object(
                2,
                [
                    model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1),
                    model.DesignationCatalogObject(design="test2"),
                ],
            ),
        ]

        self.common_repo.register_pgcs([1, 2])
        self._save_layer2_data(objects)

        actual = self.layer2_repo.query(
            [model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION],
            layer2.DesignationEqualsFilter("test2"),
            layer2.CombinedSearchParams([]),
            10,
            0,
        )
        expected = [
            model.Layer2Object(
                2,
                [
                    model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1),
                    model.DesignationCatalogObject(design="test2"),
                ],
            ),
        ]

        self.assertEqual(actual, expected)

    def test_several_filters(self):
        objects = [
            model.Layer2Object(
                1,
                [
                    model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1),
                    model.DesignationCatalogObject(design="test"),
                ],
            ),
            model.Layer2Object(
                2,
                [
                    model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1),
                    model.DesignationCatalogObject(design="test2"),
                ],
            ),
        ]

        self.common_repo.register_pgcs([1, 2])
        self._save_layer2_data(objects)

        actual = self.layer2_repo.query(
            [model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION],
            layer2.AndFilter(
                [
                    layer2.DesignationEqualsFilter("test2"),
                    layer2.ICRSCoordinatesInRadiusFilter(10),
                ]
            ),
            layer2.CombinedSearchParams(
                [
                    layer2.ICRSSearchParams(12, 12),
                ]
            ),
            10,
            0,
        )

        expected = [
            model.Layer2Object(
                2,
                [
                    model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1),
                    model.DesignationCatalogObject(design="test2"),
                ],
            )
        ]

        self.assertEqual(actual, expected)

    def test_pagination(self):
        objects: list[model.Layer2Object] = [
            model.Layer2Object(1, [model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
            model.Layer2Object(2, [model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)]),
            model.Layer2Object(3, [model.ICRSCatalogObject(ra=12, dec=12, e_ra=0.1, e_dec=0.1)]),
            model.Layer2Object(4, [model.ICRSCatalogObject(ra=13, dec=13, e_ra=0.1, e_dec=0.1)]),
            model.Layer2Object(5, [model.ICRSCatalogObject(ra=14, dec=14, e_ra=0.1, e_dec=0.1)]),
        ]

        self.common_repo.register_pgcs([1, 2, 3, 4, 5])
        self._save_layer2_data(objects)

        actual = self.layer2_repo.query(
            [model.RawCatalog.ICRS],
            layer2.ICRSCoordinatesInRadiusFilter(10),
            layer2.ICRSSearchParams(12, 12),
            2,
            1,
        )

        self.assertEqual(len(actual), 2)

    def test_batch_query(self):
        objects: list[model.Layer2Object] = [
            model.Layer2Object(1, [model.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
            model.Layer2Object(2, [model.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)]),
            model.Layer2Object(3, [model.ICRSCatalogObject(ra=12, dec=12, e_ra=0.1, e_dec=0.1)]),
            model.Layer2Object(4, [model.ICRSCatalogObject(ra=13, dec=13, e_ra=0.1, e_dec=0.1)]),
            model.Layer2Object(5, [model.ICRSCatalogObject(ra=14, dec=14, e_ra=0.1, e_dec=0.1)]),
        ]

        self.common_repo.register_pgcs([1, 2, 3, 4, 5])
        self._save_layer2_data(objects)

        actual = self.layer2_repo.query_batch(
            [model.RawCatalog.ICRS],
            {"icrs": layer2.ICRSCoordinatesInRadiusFilter(10)},
            {
                "obj1": layer2.ICRSSearchParams(10, 10),
                "obj2": layer2.ICRSSearchParams(13, 13),
            },
            20,
            0,
        )

        self.assertEqual(len(actual), 2)

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
                model.Layer2Object(1, [model.DesignationCatalogObject(design="a")]),
                model.Layer2Object(2, [model.DesignationCatalogObject(design="b")]),
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
        self.layer1_repo.save_structured_data("designation.data", ["design"], ["r1"], [["x"]])
        self._save_layer2_data([model.Layer2Object(100, [model.DesignationCatalogObject(design="x")])])

        orphaned = self.layer2_repo.get_orphaned_pgcs([model.RawCatalog.DESIGNATION])

        self.assertEqual(orphaned, {"layer2.designation": []})

    def test_get_orphaned_pgcs_returns_only_pgcs_without_layer1_data(self) -> None:
        self._get_table("t1")
        self.layer0_repo.register_records("t1", ["r1"])
        self.common_repo.register_pgcs([100, 200])
        self.layer0_repo.upsert_pgc({"r1": 100})
        self.layer1_repo.save_structured_data("designation.data", ["design"], ["r1"], [["linked"]])
        self._save_layer2_data(
            [
                model.Layer2Object(100, [model.DesignationCatalogObject(design="linked")]),
                model.Layer2Object(200, [model.DesignationCatalogObject(design="orphan")]),
            ]
        )

        orphaned = self.layer2_repo.get_orphaned_pgcs([model.RawCatalog.DESIGNATION])

        self.assertEqual(orphaned.keys(), {"layer2.designation"})
        self.assertEqual(set(orphaned["layer2.designation"]), {200})

    def test_remove_pgcs_removes_specified_pgcs(self) -> None:
        self.common_repo.register_pgcs([1, 2])
        self._save_layer2_data(
            [
                model.Layer2Object(1, [model.DesignationCatalogObject(design="d1")]),
                model.Layer2Object(2, [model.DesignationCatalogObject(design="d2")]),
            ]
        )

        self.layer2_repo.remove_pgcs([model.RawCatalog.DESIGNATION], [1])

        actual = self.layer2_repo.query(
            [model.RawCatalog.DESIGNATION],
            layer2.DesignationEqualsFilter("d1"),
            layer2.CombinedSearchParams([]),
            10,
            0,
        )
        self.assertEqual(actual, [])
        actual = self.layer2_repo.query(
            [model.RawCatalog.DESIGNATION],
            layer2.DesignationEqualsFilter("d2"),
            layer2.CombinedSearchParams([]),
            10,
            0,
        )
        self.assertEqual(actual, [model.Layer2Object(2, [model.DesignationCatalogObject(design="d2")])])

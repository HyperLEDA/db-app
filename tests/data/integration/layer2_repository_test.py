import datetime
import unittest

import structlog
from astropy import table

from app.data import model, repositories
from app.lib.storage import enums
from tests import lib


class Layer2RepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get(enums.PG_ENUM_REGISTRY)

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

        storage = self.pg_storage.get_storage()
        removed = storage.query("SELECT pgc FROM layer2.designation WHERE pgc = %s", params=[1])
        self.assertEqual(removed, [])
        remaining = storage.query("SELECT pgc, design FROM layer2.designation WHERE pgc = %s", params=[2])
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["design"], "d2")

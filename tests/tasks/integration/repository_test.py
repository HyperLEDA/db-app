import datetime
import unittest

import structlog
from astropy import table
from astropy import units as u

from app.data import model, repositories
from app.lib.storage import enums
from app.tasks import repository
from tests import lib


class RepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get(enums.PG_ENUM_REGISTRY)

        cls.common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer1_repo = repositories.Layer1Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.repo = repository.Repository(cls.pg_storage.get_storage(), structlog.get_logger())

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
            self.repo.save(table_name, table.QTable(qtable_data))

    def _get_table(self, table_name: str) -> int:
        bib_id = self.common_repo.create_bibliography("123456", 2000, ["test"], "test")
        table_resp = self.layer0_repo.create_table(model.Layer0TableMeta(table_name, [], bib_id))
        return table_resp.table_id

    def _insert_nature_data(
        self,
        table_name: str,
        record_ids: list[str],
        pgcs: dict[str, int],
        rows: list[list[str]],
    ) -> None:
        self._get_table(table_name)
        self.layer0_repo.register_records(table_name, record_ids)
        self.common_repo.register_pgcs(list(pgcs.values()))
        self.layer0_repo.upsert_pgc(pgcs)
        columns = ["type_name"]
        self.layer1_repo.save_structured_data(
            model.NatureCatalogObject.layer1_table(),
            columns,
            record_ids,
            rows,
        )

    def test_get_last_update_time_returns_stored_dt(self) -> None:
        dt_icrs = self.repo.get_last_update_time(model.RawCatalog.ICRS)
        dt_nature = self.repo.get_last_update_time(model.RawCatalog.NATURE)
        epoch = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)
        self.assertEqual(dt_icrs if dt_icrs.tzinfo else dt_icrs.replace(tzinfo=datetime.UTC), epoch)
        self.assertEqual(
            dt_nature if dt_nature.tzinfo else dt_nature.replace(tzinfo=datetime.UTC),
            epoch,
        )

    def test_update_last_update_time_updates_stored_dt(self) -> None:
        new_dt = datetime.datetime(2020, 6, 15, 12, 0, 0, tzinfo=datetime.UTC)
        self.repo.update_last_update_time(new_dt, model.RawCatalog.ICRS)

        got_icrs = self.repo.get_last_update_time(model.RawCatalog.ICRS)
        self.assertEqual(got_icrs.replace(tzinfo=None), new_dt.replace(tzinfo=None))
        got_nature = self.repo.get_last_update_time(model.RawCatalog.NATURE)
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

        orphaned = self.repo.get_orphaned_pgcs([model.RawCatalog.DESIGNATION])

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

        orphaned = self.repo.get_orphaned_pgcs([model.RawCatalog.DESIGNATION])

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

        orphaned = self.repo.get_orphaned_pgcs([model.RawCatalog.DESIGNATION])

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

        self.repo.remove_pgcs([model.RawCatalog.DESIGNATION], [1])

        storage = self.pg_storage.get_storage()
        removed = storage.query("SELECT pgc FROM layer2.designation WHERE pgc = %s", params=[1])
        self.assertEqual(removed, [])
        remaining = storage.query("SELECT pgc, design FROM layer2.designation WHERE pgc = %s", params=[2])
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["design"], "d2")

    def test_get_new_nature_records_returns_empty_when_no_nature_data(self) -> None:
        self._get_table("empty_table")
        self.layer0_repo.register_records("empty_table", ["r1"])
        self.common_repo.register_pgcs([100])
        self.layer0_repo.upsert_pgc({"r1": 100})

        result = self.repo.get_new_nature_records(datetime.datetime.fromtimestamp(0, tz=datetime.UTC), 10, 0)
        self.assertEqual(len(result), 0)

    def test_get_new_nature_records_returns_all_when_dt_is_epoch(self) -> None:
        self._insert_nature_data(
            "t1",
            ["rec1", "rec2"],
            {"rec1": 1001, "rec2": 1002},
            [["G"], ["QSO"]],
        )

        result = self.repo.get_new_nature_records(datetime.datetime.fromtimestamp(0, tz=datetime.UTC), 10, 0)

        self.assertEqual(len(result), 2)
        by_pgc = {int(pgc): str(type_name) for pgc, type_name in zip(result["pgc"], result["type_name"], strict=True)}
        self.assertEqual(by_pgc[1001], "G")
        self.assertEqual(by_pgc[1002], "QSO")

    def test_get_new_nature_records_returns_empty_when_dt_is_in_future(self) -> None:
        self._insert_nature_data(
            "t1",
            ["rec1"],
            {"rec1": 1001},
            [["G"]],
        )

        future = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=1)
        result = self.repo.get_new_nature_records(future, 10, 0)

        self.assertEqual(len(result), 0)

    def test_get_new_nature_records_respects_limit_and_offset_by_pgc(self) -> None:
        self._insert_nature_data(
            "t1",
            ["r1", "r2", "r3"],
            {"r1": 10, "r2": 20, "r3": 30},
            [["G"], ["*"], ["?"]],
        )
        dt = datetime.datetime.fromtimestamp(0, tz=datetime.UTC)

        first_batch = self.repo.get_new_nature_records(dt, limit=1, offset=0)
        self.assertEqual(len(first_batch), 1)
        self.assertEqual(int(first_batch["pgc"][0]), 10)
        self.assertEqual(str(first_batch["type_name"][0]), "G")

        second_batch = self.repo.get_new_nature_records(dt, limit=1, offset=10)
        self.assertEqual(len(second_batch), 1)
        self.assertEqual(int(second_batch["pgc"][0]), 20)
        self.assertEqual(str(second_batch["type_name"][0]), "*")

        third_batch = self.repo.get_new_nature_records(dt, limit=1, offset=20)
        self.assertEqual(len(third_batch), 1)
        self.assertEqual(int(third_batch["pgc"][0]), 30)

    def test_get_new_nature_records_returns_all_records_for_same_pgc_in_one_batch(
        self,
    ) -> None:
        self._insert_nature_data(
            "t1",
            ["r1", "r2"],
            {"r1": 99, "r2": 99},
            [["G"], ["*"]],
        )

        result = self.repo.get_new_nature_records(
            datetime.datetime.fromtimestamp(0, tz=datetime.UTC), limit=10, offset=0
        )

        self.assertEqual(len(result), 2)
        self.assertEqual({int(pgc) for pgc in result["pgc"]}, {99})
        self.assertEqual({str(t) for t in result["type_name"]}, {"G", "*"})

    def test_get_new_redshift_records_defaults_null_e_cz(self) -> None:
        self._get_table("cz_table")
        self.layer0_repo.register_records("cz_table", ["r1", "r2"])
        self.common_repo.register_pgcs([10, 20])
        self.layer0_repo.upsert_pgc({"r1": 10, "r2": 20})
        self.layer1_repo.save_structured_data(
            model.RedshiftCatalogObject.layer1_table(),
            model.RedshiftCatalogObject.layer1_keys(),
            ["r1", "r2"],
            [[1000.0, 10.0], [2000.0, None]],
            conflict_keys=model.RedshiftCatalogObject.layer1_primary_keys(),
        )

        result = self.repo.get_new_redshift_records(
            datetime.datetime.fromtimestamp(0, tz=datetime.UTC), limit=10, offset=0
        )

        self.assertEqual(len(result), 2)
        by_pgc = {
            int(pgc): (float(cz.to_value(u.Unit("km/s"))), float(e_cz.to_value(u.Unit("km/s"))))
            for pgc, cz, e_cz in zip(result["pgc"], result["cz"], result["e_cz"], strict=True)
        }
        self.assertEqual(by_pgc, {10: (1000.0, 10.0), 20: (2000.0, 100.0)})

    def test_save_structured_data_bumps_pgc_modification_time(self) -> None:
        self._insert_nature_data("t_bump", ["rec1"], {"rec1": 5001}, [["G"]])
        old_dt = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
        self.pg_storage.storage.exec(
            "UPDATE common.pgc SET modification_time = %s WHERE id = %s",
            params=[old_dt, 5001],
        )

        self.layer1_repo.save_structured_data(
            model.NatureCatalogObject.layer1_table(),
            ["type_name"],
            ["rec1"],
            [["QSO"]],
        )

        row = self.pg_storage.storage.query_one(
            "SELECT modification_time FROM common.pgc WHERE id = %s",
            params=[5001],
        )
        self.assertGreater(row["modification_time"].replace(tzinfo=datetime.UTC), old_dt)

        after_old = self.repo.get_new_nature_records(datetime.datetime(2000, 1, 2, tzinfo=datetime.UTC), 10, 0)
        self.assertEqual(len(after_old), 1)
        self.assertEqual(int(after_old["pgc"][0]), 5001)

        future = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=1)
        self.assertEqual(len(self.repo.get_new_nature_records(future, 10, 0)), 0)

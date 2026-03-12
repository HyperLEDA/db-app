import datetime
import unittest

import structlog
from astropy import units as u

from app.data import model, repositories
from app.lib.storage import enums
from tests import lib


class Layer1RepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()

        cls.common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer1_repo = repositories.Layer1Repository(cls.pg_storage.get_storage(), structlog.get_logger())

    def tearDown(self):
        self.pg_storage.clear()

    def _get_table(self, table_name: str) -> int:
        bib_id = self.common_repo.create_bibliography("123456", 2000, ["test"], "test")
        table_resp = self.layer0_repo.create_table(model.Layer0TableMeta(table_name, [], bib_id))
        return table_resp.table_id

    def _insert_nature_data(
        self,
        table_name: str,
        record_ids: list[str],
        pgcs: dict[str, int],
        records: list[model.Record],
    ) -> None:
        self._get_table(table_name)
        self.layer0_repo.register_records(table_name, record_ids)
        self.common_repo.register_pgcs(list(pgcs.values()))
        self.layer0_repo.upsert_pgc(pgcs)
        columns = model.NatureCatalogObject.layer1_keys()
        self.layer1_repo.save_structured_data(
            model.NatureCatalogObject.layer1_table(),
            columns,
            [r.id for r in records],
            [[r.data[0].layer1_data()[c] for c in columns] for r in records],
        )

    def test_icrs(self):
        bib_id = self.common_repo.create_bibliography("123456", 2000, ["test"], "test")
        _ = self.layer0_repo.create_table(
            model.Layer0TableMeta(
                "test_table",
                [
                    model.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit=u.Unit("hour")),
                    model.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit=u.Unit("hour")),
                    model.ColumnDescription("e_ra", "float", ucd="stat.error", unit=u.Unit("hour")),
                    model.ColumnDescription("e_dec", "float", ucd="stat.error", unit=u.Unit("hour")),
                ],
                bib_id,
                enums.DataType.REGULAR,
            )
        )
        self.layer0_repo.register_records("test_table", ["111", "112"])
        columns = model.ICRSCatalogObject.layer1_keys()
        self.layer1_repo.save_structured_data(
            model.ICRSCatalogObject.layer1_table(),
            columns,
            ["111", "112"],
            [[12.1, 0.1, 1, 0.3], [11.1, 0.2, 2, 0.4]],
        )

        result = self.pg_storage.storage.query("SELECT ra FROM icrs.data ORDER BY ra")
        self.assertEqual(result, [{"ra": 11.1}, {"ra": 12.1}])

    def test_get_new_nature_records_returns_empty_when_no_nature_data(self) -> None:
        self._get_table("empty_table")
        self.layer0_repo.register_records("empty_table", ["r1"])
        self.common_repo.register_pgcs([100])
        self.layer0_repo.upsert_pgc({"r1": 100})

        result = self.layer1_repo.get_new_nature_records(datetime.datetime.fromtimestamp(0, tz=datetime.UTC), 10, 0)
        self.assertEqual(result, [])

    def test_get_new_nature_records_returns_all_when_dt_is_epoch(self) -> None:
        self._insert_nature_data(
            "t1",
            ["rec1", "rec2"],
            {"rec1": 1001, "rec2": 1002},
            [
                model.Record("rec1", [model.NatureCatalogObject(type_name="G")]),
                model.Record("rec2", [model.NatureCatalogObject(type_name="QSO")]),
            ],
        )

        result = self.layer1_repo.get_new_nature_records(datetime.datetime.fromtimestamp(0, tz=datetime.UTC), 10, 0)

        self.assertEqual(len(result), 2)
        by_pgc = {r.pgc: r for r in result}
        self.assertEqual(by_pgc[1001], model.StructuredData(1001, "rec1", model.NatureRecord("G")))
        self.assertEqual(by_pgc[1002], model.StructuredData(1002, "rec2", model.NatureRecord("QSO")))

    def test_get_new_nature_records_returns_empty_when_dt_is_in_future(self) -> None:
        self._insert_nature_data(
            "t1",
            ["rec1"],
            {"rec1": 1001},
            [model.Record("rec1", [model.NatureCatalogObject(type_name="G")])],
        )

        future = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=1)
        result = self.layer1_repo.get_new_nature_records(future, 10, 0)

        self.assertEqual(result, [])

    def test_get_new_nature_records_respects_limit_and_offset_by_pgc(self) -> None:
        self._insert_nature_data(
            "t1",
            ["r1", "r2", "r3"],
            {"r1": 10, "r2": 20, "r3": 30},
            [
                model.Record("r1", [model.NatureCatalogObject(type_name="G")]),
                model.Record("r2", [model.NatureCatalogObject(type_name="*")]),
                model.Record("r3", [model.NatureCatalogObject(type_name="?")]),
            ],
        )
        dt = datetime.datetime.fromtimestamp(0, tz=datetime.UTC)

        first_batch = self.layer1_repo.get_new_nature_records(dt, limit=1, offset=0)
        self.assertEqual(len(first_batch), 1)
        self.assertEqual(first_batch[0].pgc, 10)
        self.assertEqual(first_batch[0].record_id, "r1")
        self.assertEqual(first_batch[0].data.type_name, "G")

        second_batch = self.layer1_repo.get_new_nature_records(dt, limit=1, offset=10)
        self.assertEqual(len(second_batch), 1)
        self.assertEqual(second_batch[0].pgc, 20)
        self.assertEqual(second_batch[0].data.type_name, "*")

        third_batch = self.layer1_repo.get_new_nature_records(dt, limit=1, offset=20)
        self.assertEqual(len(third_batch), 1)
        self.assertEqual(third_batch[0].pgc, 30)

    def test_get_new_nature_records_returns_all_records_for_same_pgc_in_one_batch(
        self,
    ) -> None:
        self._insert_nature_data(
            "t1",
            ["r1", "r2"],
            {"r1": 99, "r2": 99},
            [
                model.Record("r1", [model.NatureCatalogObject(type_name="G")]),
                model.Record("r2", [model.NatureCatalogObject(type_name="*")]),
            ],
        )

        result = self.layer1_repo.get_new_nature_records(
            datetime.datetime.fromtimestamp(0, tz=datetime.UTC), limit=10, offset=0
        )

        self.assertEqual(len(result), 2)
        self.assertEqual({r.pgc for r in result}, {99})
        type_names = {r.data.type_name for r in result}
        self.assertEqual(type_names, {"G", "*"})

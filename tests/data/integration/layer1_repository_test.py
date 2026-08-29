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
        cls.pg_storage = lib.TestPostgresStorage.get(enums.PG_ENUM_REGISTRY)

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

    def test_designation_multiple_names_per_record(self) -> None:
        self._get_table("desig_table")
        self.layer0_repo.register_records("desig_table", ["r1"])
        self.layer1_repo.save_structured_data(
            model.DesignationCatalogObject.layer1_table(),
            model.DesignationCatalogObject.layer1_keys(),
            ["r1", "r1"],
            [["NGC 224"], ["M 31"]],
            conflict_keys=model.DesignationCatalogObject.layer1_primary_keys(),
        )

        result = self.pg_storage.storage.query(
            "SELECT design FROM designation.data WHERE record_id = %s ORDER BY design",
            params=["r1"],
        )

        self.assertEqual(result, [{"design": "M 31"}, {"design": "NGC 224"}])

    def test_get_redshift_records_defaults_null_e_cz(self) -> None:
        self._get_table("cz_table")
        self.layer0_repo.register_records("cz_table", ["r1", "r2"])
        self.layer1_repo.save_structured_data(
            model.RedshiftCatalogObject.layer1_table(),
            model.RedshiftCatalogObject.layer1_keys(),
            ["r1", "r2"],
            [[1000.0, 10.0], [2000.0, None]],
            conflict_keys=model.RedshiftCatalogObject.layer1_primary_keys(),
        )

        result = self.layer1_repo.get_redshift_records(["r1", "r2", "missing"])

        self.assertEqual(len(result), 3)
        self.assertIsNotNone(result[0])
        self.assertIsNotNone(result[1])
        self.assertIsNone(result[2])
        assert result[0] is not None
        assert result[1] is not None
        self.assertEqual(result[0].cz, 1000.0)
        self.assertEqual(result[0].e_cz, 10.0)
        self.assertEqual(result[1].cz, 2000.0)
        self.assertEqual(result[1].e_cz, 100.0)

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

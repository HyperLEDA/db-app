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

    def test_icrs(self):
        objects: list[model.Record] = [
            model.Record("111", [model.ICRSCatalogObject(ra=12.1, dec=1, e_ra=0.1, e_dec=0.3)]),
            model.Record("112", [model.ICRSCatalogObject(ra=11.1, dec=2, e_ra=0.2, e_dec=0.4)]),
        ]

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
        self.layer1_repo.save_data(objects)

        result = self.pg_storage.storage.query("SELECT ra FROM icrs.data ORDER BY ra")
        self.assertEqual(result, [{"ra": 11.1}, {"ra": 12.1}])

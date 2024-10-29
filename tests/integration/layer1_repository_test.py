import unittest

import structlog
from astropy import units as u

from app import commands, entities
from app.data import model, repositories
from app.lib import testing
from app.lib.storage import enums


class Layer1RepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = testing.get_test_postgres_storage()

        cls.depot = commands.get_mock_depot()
        cls.depot.common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.depot.layer0_repo = repositories.Layer0Repository(
            cls.depot.common_repo, cls.pg_storage.get_storage(), structlog.get_logger()
        )
        cls.depot.layer1_repo = repositories.Layer1Repository(cls.pg_storage.get_storage(), structlog.get_logger())

    def tearDown(self):
        self.pg_storage.clear()

    def test_icrs(self):
        objects = [
            model.Layer1CatalogObject(pgc=1, object_id="111", data={"ra": 12.1, "dec": 1, "e_ra": 0.1, "e_dec": 0.3}),
            model.Layer1CatalogObject(pgc=1, object_id="111", data={"ra": 11.1, "dec": 2, "e_ra": 0.2, "e_dec": 0.4}),
        ]

        bib_id = self.depot.common_repo.create_bibliography("123456", 2000, ["test"], "test")
        table_resp = self.depot.layer0_repo.create_table(
            entities.Layer0Creation(
                "test_table",
                [
                    entities.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit=u.hour),
                    entities.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit=u.hour),
                    entities.ColumnDescription("e_ra", "float", ucd="stat.error", unit=u.hour),
                    entities.ColumnDescription("e_dec", "float", ucd="stat.error", unit=u.hour),
                ],
                bib_id,
                enums.DataType.REGULAR,
            )
        )
        self.depot.layer0_repo.upsert_object(
            table_resp.table_id,
            entities.ObjectProcessingInfo("111", enums.ObjectProcessingStatus.EXISTING, {}, 1),
        )
        self.depot.common_repo.upsert_pgc([1])

        self.depot.layer1_repo.save_data(model.Layer1Catalog.ICRS, objects)

        result = self.pg_storage.storage.query("SELECT ra FROM icrs.data")
        self.assertEqual(result, [{"ra": 12.1}, {"ra": 11.1}])

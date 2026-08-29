import unittest

import structlog

from app.data import model, repositories
from app.dataapi.repository import Repository
from tests import lib


class RepositoryPhotometryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()
        cls.common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer1_repo = repositories.Layer1Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.repo = Repository(cls.pg_storage.get_storage())

    def tearDown(self) -> None:
        self.pg_storage.clear()

    def _get_table(self, table_name: str) -> int:
        bib_id = self.common_repo.create_bibliography("123456", 2000, ["test"], "test")
        table_resp = self.layer0_repo.create_table(model.Layer0TableMeta(table_name, [], bib_id))
        return table_resp.table_id

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

        result = self.repo.query_pgc([model.RawCatalog.PHOTOMETRY__TOTAL], [5001], limit=10)

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
